"""Flask API for website cloning"""

import base64
from pathlib import Path
from flask import Flask, request, jsonify
from .cloner import clone_website
from .utils.logger import logger
from .config import config


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)

    app.config.update(
        DEBUG=config.FLASK_DEBUG,
        JSON_SORT_KEYS=False,
    )

    @app.route("/", methods=["GET"])
    def index():
        """API information endpoint"""
        return jsonify({
            "name": "WordPress Website Cloner API",
            "version": "2.0.0",
            "endpoints": {
                "clone_url": "/clone?url=<url>",
                "clone_base64": "/clone/<base64_url>",
                "health": "/health"
            }
        })

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        return jsonify({"status": "healthy"})

    @app.route("/clone", methods=["GET", "POST"])
    def clone_from_query():
        """
        Clone website from query parameter or JSON body

        Query: /clone?url=https://example.com
        Body: {"url": "https://example.com", "headless": true}
        """
        try:
            # Get URL from query or body
            if request.method == "GET":
                url = request.args.get("url")
                headless = request.args.get("headless", "true").lower() == "true"
            else:
                data = request.get_json() or {}
                url = data.get("url")
                headless = data.get("headless", True)

            if not url:
                return jsonify({
                    "error": "URL parameter is required",
                    "usage": "/clone?url=https://example.com"
                }), 400

            logger.info(f"API: Cloning request for {url}")

            # Clone the website
            output_path = clone_website(url, headless=headless)

            return jsonify({
                "status": "success",
                "url": url,
                "output_path": str(output_path),
                "index_file": str(output_path / "index.html")
            })

        except Exception as e:
            logger.error(f"API: Clone failed: {e}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    @app.route("/clone/<base64_url>", methods=["GET"])
    def clone_from_base64(base64_url: str):
        """
        Clone website from base64-encoded URL

        Example: /clone/aHR0cHM6Ly9leGFtcGxlLmNvbQ==
        """
        try:
            # Decode base64 URL
            url = base64.b64decode(base64_url).decode('utf-8')
            logger.info(f"API: Decoded URL: {url}")

            # Clone the website
            output_path = clone_website(url, headless=True)

            return jsonify({
                "status": "success",
                "url": url,
                "base64_url": base64_url,
                "output_path": str(output_path),
                "index_file": str(output_path / "index.html")
            })

        except Exception as e:
            logger.error(f"API: Clone failed: {e}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    return app


def run_server(host: str = None, port: int = None, debug: bool = None):
    """
    Run the Flask development server

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    host = host or config.FLASK_HOST
    port = port or config.FLASK_PORT
    debug = debug if debug is not None else config.FLASK_DEBUG

    app = create_app()
    logger.info(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
