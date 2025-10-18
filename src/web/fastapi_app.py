"""FastAPI Web UI for WordPress Cloner"""

import asyncio
import base64
import json
import queue
import threading
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
import uvicorn
from loguru import logger

from ..cloner import clone_website
from ..config import config


# Request/Response models
class CloneRequest(BaseModel):
    url: HttpUrl
    headless: bool = True


class CloneResponse(BaseModel):
    status: str
    url: str
    project_folder: str
    preview_url: str
    message: Optional[str] = None


class CloneStatus(BaseModel):
    status: str  # "cloning", "completed", "error"
    progress: int  # 0-100
    message: str
    preview_url: Optional[str] = None


# Global clone status tracking (in production, use Redis or similar)
clone_jobs = {}
log_queues = {}  # Store log queues for each job
cancel_flags = {}  # Store cancel flags for each job
log_handler_ids = {}  # Store log handler IDs for each job to prevent duplicates


class QueueLogHandler:
    """Custom log handler that sends logs to a queue"""
    def __init__(self, log_queue: queue.Queue):
        self.log_queue = log_queue

    def write(self, message):
        """Handler for log messages"""
        if message and message.strip():
            try:
                self.log_queue.put_nowait(message.strip())
            except:
                pass


def clone_with_logging(url: str, headless: bool, job_id: str):
    """Clone website and capture logs to queue"""
    # Remove old handler if it exists to prevent duplicate log captures
    if job_id in log_handler_ids:
        old_handler_id = log_handler_ids[job_id]
        try:
            logger.remove(old_handler_id)
            print(f"[DEBUG] Removed old log handler {old_handler_id} for job {job_id}")
        except:
            pass  # Handler might have already been removed
        del log_handler_ids[job_id]

    # Get or create log queue
    if job_id not in log_queues:
        log_queues[job_id] = queue.Queue()

    log_q = log_queues[job_id]

    # Add custom log handler that captures just the message
    def log_sink(message):
        """Custom sink that extracts just the log message"""
        # Extract the actual message from the formatted log
        try:
            msg_text = message.record['message']
            if msg_text and msg_text.strip():
                log_q.put_nowait(msg_text)
                print(f"[LOG SINK] Captured: {msg_text[:80]}")  # Debug output
        except Exception as e:
            # If extraction fails, try to get the raw message
            try:
                log_q.put_nowait(str(message))
            except:
                pass

    print(f"[DEBUG] Adding log handler for job {job_id}")
    handler_id = logger.add(
        log_sink,
        level="INFO",  # Only capture INFO and above (excludes DEBUG messages)
        format="{message}",
        filter=None,  # Accept all modules
        enqueue=False  # Don't enqueue to avoid threading issues
    )
    log_handler_ids[job_id] = handler_id  # Store handler ID
    print(f"[DEBUG] Log handler added with ID: {handler_id}")

    try:
        log_q.put_nowait("Starting clone process...")
        log_q.put_nowait(f"Target URL: {url}")
        result = clone_website(url, headless)
        log_q.put_nowait("Clone completed successfully!")
        return result
    except Exception as e:
        log_q.put_nowait(f"Error: {str(e)}")
        raise
    finally:
        logger.remove(handler_id)
        if job_id in log_handler_ids and log_handler_ids[job_id] == handler_id:
            del log_handler_ids[job_id]


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="WordPress Website Cloner",
        description="Clone any website with all its assets",
        version="2.0.0",
    )

    # Setup paths
    web_dir = Path(__file__).parent
    templates_dir = web_dir / "templates"
    static_dir = web_dir / "static"

    # Setup Jinja2 templates
    templates = Jinja2Templates(directory=str(templates_dir))

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Mount cloned projects directory
    if config.PROJECT_DIR.exists():
        app.mount(
            "/cloned",
            StaticFiles(directory=str(config.PROJECT_DIR)),
            name="cloned"
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main page with cloning interface"""
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "WordPress Cloner"}
        )

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "version": "2.0.0"}

    @app.post("/api/clone", response_model=CloneResponse)
    async def clone_website_api(clone_request: CloneRequest):
        """
        Clone a website (async endpoint)
        """
        url = str(clone_request.url)
        # Create job_id matching frontend encoding (removes trailing =)
        job_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')

        # If a clone with this job_id is already running, cancel it
        if job_id in clone_jobs:
            old_status = clone_jobs[job_id].get("status")
            if old_status == "cloning":
                logger.warning(f"Cancelling existing clone job: {job_id}")
                cancel_flags[job_id] = True
                # Wait a moment for the old job to notice cancellation
                await asyncio.sleep(0.5)

        # Clear old queue if it exists and create fresh one
        if job_id in log_queues:
            # Drain old queue
            while not log_queues[job_id].empty():
                try:
                    log_queues[job_id].get_nowait()
                except:
                    break

        # Initialize job status and log queue
        clone_jobs[job_id] = {
            "status": "cloning",
            "progress": 0,
            "message": "Starting clone process...",
            "url": url
        }
        log_queues[job_id] = queue.Queue()
        cancel_flags[job_id] = False  # Clear cancel flag for new job

        try:
            logger.info(f"Web UI: Starting clone of {url}")

            # Update progress
            clone_jobs[job_id]["progress"] = 20
            clone_jobs[job_id]["message"] = "Loading website..."

            # Run clone in thread pool (since it's sync)
            loop = asyncio.get_event_loop()
            output_path = await loop.run_in_executor(
                None,
                clone_with_logging,
                url,
                clone_request.headless,
                job_id
            )

            # Update progress
            clone_jobs[job_id]["progress"] = 100
            clone_jobs[job_id]["status"] = "completed"
            clone_jobs[job_id]["message"] = "Clone completed successfully!"

            # Generate preview URL
            project_folder = output_path.name
            preview_url = f"/cloned/{project_folder}/index.html"
            clone_jobs[job_id]["preview_url"] = preview_url

            logger.success(f"Web UI: Clone completed - {url}")

            return CloneResponse(
                status="success",
                url=url,
                project_folder=project_folder,
                preview_url=preview_url,
                message="Website cloned successfully!"
            )

        except Exception as e:
            logger.error(f"Web UI: Clone failed - {e}")
            clone_jobs[job_id]["status"] = "error"
            clone_jobs[job_id]["progress"] = 0
            clone_jobs[job_id]["message"] = f"Error: {str(e)}"

            raise HTTPException(
                status_code=500,
                detail=f"Failed to clone website: {str(e)}"
            )

    @app.get("/api/status/{job_id}", response_model=CloneStatus)
    async def get_clone_status(job_id: str):
        """Get status of a clone job"""
        if job_id not in clone_jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = clone_jobs[job_id]
        return CloneStatus(
            status=job["status"],
            progress=job["progress"],
            message=job["message"],
            preview_url=job.get("preview_url")
        )

    @app.get("/api/projects")
    async def list_projects():
        """List all cloned projects"""
        try:
            if not config.PROJECT_DIR.exists():
                return {"projects": []}

            projects = []
            for project_dir in config.PROJECT_DIR.iterdir():
                if project_dir.is_dir():
                    index_file = project_dir / "index.html"
                    if index_file.exists():
                        # Decode base64 folder name to get original URL
                        try:
                            url = base64.b64decode(project_dir.name).decode('utf-8')
                        except:
                            url = "Unknown URL"

                        projects.append({
                            "name": project_dir.name,
                            "url": url,
                            "preview_url": f"/cloned/{project_dir.name}/index.html",
                            "created": project_dir.stat().st_mtime
                        })

            # Sort by creation time (newest first)
            projects.sort(key=lambda x: x["created"], reverse=True)

            return {"projects": projects}

        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/projects/{project_name}")
    async def delete_project(project_name: str):
        """Delete a cloned project"""
        try:
            project_path = config.PROJECT_DIR / project_name
            if not project_path.exists():
                raise HTTPException(status_code=404, detail="Project not found")

            # Delete the directory
            import shutil
            shutil.rmtree(project_path)

            logger.info(f"Deleted project: {project_name}")
            return {"status": "success", "message": "Project deleted"}

        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/debug/queues")
    async def debug_queues():
        """Debug endpoint to see all active queues"""
        return {
            "log_queues": list(log_queues.keys()),
            "clone_jobs": list(clone_jobs.keys()),
            "cancel_flags": list(cancel_flags.keys()),
            "log_handler_ids": {k: v for k, v in log_handler_ids.items()}
        }

    @app.get("/api/logs/{job_id}/test")
    async def test_logs(job_id: str):
        """Test endpoint to check if logs are in queue"""
        if job_id not in log_queues:
            return {
                "error": "Queue not found",
                "job_id": job_id,
                "available_queues": list(log_queues.keys()),
                "clone_jobs": list(clone_jobs.keys())
            }

        log_q = log_queues[job_id]

        return {
            "job_id": job_id,
            "queue_size": log_q.qsize(),
            "queue_empty": log_q.empty()
        }

    @app.get("/api/logs/{job_id}")
    async def stream_logs(job_id: str):
        """Stream clone logs via Server-Sent Events"""
        # Create log queue for this job if it doesn't exist
        # Note: Job might not exist yet (race condition), so we create the queue early
        if job_id not in log_queues:
            log_queues[job_id] = queue.Queue()
            logger.debug(f"Created log queue for job: {job_id}")

        async def event_generator():
            log_q = log_queues[job_id]
            print(f"[SSE] Starting event generator for job {job_id}, queue size: {log_q.qsize()}")
            try:
                while True:
                    # Check if job is done
                    if job_id in clone_jobs:
                        status = clone_jobs[job_id].get("status")
                        if status in ["completed", "error"]:
                            # Drain remaining messages before closing
                            while not log_q.empty():
                                try:
                                    message = log_q.get_nowait()
                                    data = json.dumps({"type": "log", "message": message})
                                    yield f"data: {data}\n\n"
                                except queue.Empty:
                                    break
                            # Send final status and close
                            data = json.dumps({"type": "status", "status": status})
                            print(f"[SSE] Sending final status: {status}")
                            yield f"data: {data}\n\n"
                            break

                    # Try to get log messages
                    qsize = log_q.qsize()
                    if qsize > 0:
                        print(f"[SSE] Queue has {qsize} messages")

                    # Try to drain all available messages
                    messages_sent = 0
                    while not log_q.empty():
                        try:
                            message = log_q.get_nowait()
                            # Properly encode message as JSON
                            data = json.dumps({"type": "log", "message": message})
                            print(f"[SSE] Sending: {message[:50]}")
                            yield f"data: {data}\n\n"
                            messages_sent += 1
                        except queue.Empty:
                            break

                    if messages_sent == 0:
                        # Send heartbeat
                        yield f": heartbeat\n\n"

                    await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                print(f"[SSE] Event generator cancelled for job {job_id}")
                pass
            except Exception as e:
                print(f"[SSE] Error in event generator: {e}")
                pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    @app.post("/api/cancel/{job_id}")
    async def cancel_clone(job_id: str):
        """Cancel a running clone job"""
        if job_id not in clone_jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        # Set cancel flag
        cancel_flags[job_id] = True

        # Update job status
        if clone_jobs[job_id]["status"] == "cloning":
            clone_jobs[job_id]["status"] = "cancelled"
            clone_jobs[job_id]["message"] = "Clone cancelled by user"

            # Send message to log queue
            if job_id in log_queues:
                try:
                    log_queues[job_id].put_nowait("Clone cancelled by user")
                except:
                    pass

        logger.info(f"Clone job cancelled: {job_id}")
        return {"status": "success", "message": "Clone job cancelled"}

    @app.get("/browse/{project_name}")
    async def browse_files(request: Request, project_name: str):
        """File browser page for a project"""
        project_path = config.PROJECT_DIR / project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        return templates.TemplateResponse(
            "browser.html",
            {
                "request": request,
                "project_name": project_name,
                "title": "File Browser"
            }
        )

    @app.get("/api/files/{project_name}")
    async def list_files(project_name: str, path: str = ""):
        """List files in a project directory"""
        try:
            project_path = config.PROJECT_DIR / project_name
            if not project_path.exists():
                raise HTTPException(status_code=404, detail="Project not found")

            # Get the directory to list
            target_path = project_path / path if path else project_path
            if not target_path.exists() or not target_path.is_dir():
                raise HTTPException(status_code=404, detail="Directory not found")

            # List files and directories
            items = []
            for item in sorted(target_path.iterdir()):
                rel_path = item.relative_to(project_path)
                items.append({
                    "name": item.name,
                    "path": str(rel_path).replace("\\", "/"),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": item.stat().st_mtime
                })

            return {
                "current_path": path,
                "items": items,
                "project_name": project_name
            }

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/manifest/{project_name}")
    async def get_manifest(project_name: str):
        """Get download manifest for a project"""
        try:
            project_path = config.PROJECT_DIR / project_name
            if not project_path.exists():
                raise HTTPException(status_code=404, detail="Project not found")

            manifest_path = project_path / "download_manifest.json"
            if not manifest_path.exists():
                return {
                    "exists": False,
                    "message": "No manifest file found"
                }

            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            return {
                "exists": True,
                "manifest": manifest_data
            }

        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the FastAPI development server

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload
    """
    logger.info(f"Starting FastAPI Web UI on http://{host}:{port}")
    uvicorn.run(
        "src.web.fastapi_app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True
    )


if __name__ == "__main__":
    run_server(reload=True)
