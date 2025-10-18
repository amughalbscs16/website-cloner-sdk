"""
Custom integration example - Send stats to external systems

This example shows how to integrate the cloner with external services like:
- Databases
- Monitoring systems
- Message queues
- Webhooks
"""

import json
from datetime import datetime
from src import ClonerSDK, ClonerEvents


class DatabaseIntegration:
    """Simulated database integration"""

    def insert_clone_job(self, job_id, url):
        """Simulated database insert"""
        print(f"[DB] Inserting clone job: {job_id} - {url}")

    def update_clone_progress(self, job_id, percentage, message):
        """Simulated progress update"""
        # In real app, this would update database
        pass

    def update_clone_status(self, job_id, status, data):
        """Simulated status update"""
        print(f"[DB] Updating job {job_id}: status={status}")

    def insert_download_stat(self, job_id, url, status, file_type):
        """Insert download statistics"""
        # In real app, track each download
        pass


class MonitoringService:
    """Simulated monitoring service (like Prometheus, DataDog, etc.)"""

    def record_metric(self, metric_name, value, tags=None):
        """Record a metric"""
        tags_str = f" {tags}" if tags else ""
        print(f"[MONITOR] {metric_name}={value}{tags_str}")

    def record_duration(self, operation, duration_seconds):
        """Record operation duration"""
        self.record_metric(f"{operation}.duration", duration_seconds)

    def increment_counter(self, counter_name, tags=None):
        """Increment a counter"""
        self.record_metric(counter_name, 1, tags)


class WebhookService:
    """Simulated webhook service"""

    def send_webhook(self, event, data):
        """Send webhook notification"""
        print(f"[WEBHOOK] {event}: {json.dumps(data, indent=2)}")


class IntegratedCloner:
    """Cloner with external integrations"""

    def __init__(self, headless=True):
        self.cloner = ClonerSDK(headless=headless)
        self.db = DatabaseIntegration()
        self.monitor = MonitoringService()
        self.webhook = WebhookService()
        self.job_id = None
        self.setup_integrations()

    def setup_integrations(self):
        """Setup event handlers for integrations"""

        @self.cloner.on_start
        def on_start(data):
            # Generate job ID
            self.job_id = f"clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Insert into database
            self.db.insert_clone_job(self.job_id, data.url)

            # Send webhook
            self.webhook.send_webhook("clone.started", {
                "job_id": self.job_id,
                "url": data.url,
                "headless": data.headless
            })

            # Record monitoring metric
            self.monitor.increment_counter("cloner.jobs.started")

        @self.cloner.on_progress
        def on_progress(data):
            # Update database with progress
            self.db.update_clone_progress(self.job_id, data.percentage, data.message)

            # Record progress metric
            self.monitor.record_metric("cloner.progress.percentage", data.percentage, {
                "job_id": self.job_id,
                "stage": data.stage
            })

        @self.cloner.on_resource_downloaded
        def on_resource_downloaded(data):
            # Track each download in database
            self.db.insert_download_stat(
                self.job_id,
                data.url,
                "success",
                data.file_type
            )

            # Increment download counter
            self.monitor.increment_counter("cloner.downloads.success", {
                "file_type": data.file_type or "unknown"
            })

        @self.cloner.on_resource_failed
        def on_resource_failed(data):
            # Track failed downloads
            self.db.insert_download_stat(
                self.job_id,
                data.url,
                "failed",
                data.file_type
            )

            # Increment failure counter
            self.monitor.increment_counter("cloner.downloads.failed")

        @self.cloner.on_stats_update
        def on_stats_update(data):
            # Send real-time stats to monitoring
            self.monitor.record_metric("cloner.resources.total", data.total_resources, {
                "job_id": self.job_id
            })
            self.monitor.record_metric("cloner.resources.success", data.successful_downloads, {
                "job_id": self.job_id
            })
            self.monitor.record_metric("cloner.resources.failed", data.failed_downloads, {
                "job_id": self.job_id
            })

        @self.cloner.on_complete
        def on_complete(data):
            # Update database
            self.db.update_clone_status(self.job_id, "completed", {
                "duration": data.duration_seconds,
                "total_resources": data.total_resources,
                "successful_downloads": data.successful_downloads,
                "failed_downloads": data.failed_downloads,
                "output_path": data.output_path
            })

            # Send webhook
            self.webhook.send_webhook("clone.completed", {
                "job_id": self.job_id,
                "url": data.url,
                "duration_seconds": data.duration_seconds,
                "statistics": {
                    "total": data.total_resources,
                    "success": data.successful_downloads,
                    "failed": data.failed_downloads
                }
            })

            # Record duration metric
            self.monitor.record_duration("cloner.job", data.duration_seconds)
            self.monitor.increment_counter("cloner.jobs.completed")

        @self.cloner.on_error
        def on_error(data):
            # Update database
            self.db.update_clone_status(self.job_id, "failed", {
                "error": data.error
            })

            # Send webhook
            self.webhook.send_webhook("clone.failed", {
                "job_id": self.job_id,
                "url": data.url,
                "error": data.error
            })

            # Record error metric
            self.monitor.increment_counter("cloner.jobs.failed")

    def clone(self, url: str):
        """Clone website with full integration"""
        print(f"\n{'='*60}")
        print(f"Cloning with integrations: {url}")
        print(f"{'='*60}\n")

        return self.cloner.clone(url)


if __name__ == "__main__":
    # Create integrated cloner
    cloner = IntegratedCloner(headless=True)

    # Clone website - all events will be sent to external systems
    try:
        output = cloner.clone("https://example.com")
        print(f"\n✅ Success! Output: {output}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

    print("\n" + "="*60)
    print("All events were sent to:")
    print("  - Database (for job tracking)")
    print("  - Monitoring service (for metrics)")
    print("  - Webhook service (for notifications)")
    print("="*60)
