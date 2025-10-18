"""
Batch cloning example - Clone multiple websites

This example shows how to clone multiple websites with progress tracking.
"""

import json
from pathlib import Path
from datetime import datetime
from src import ClonerSDK, ClonerEvents


class BatchCloner:
    """Batch website cloner with progress tracking"""

    def __init__(self, headless=True):
        self.cloner = ClonerSDK(headless=headless)
        self.results = []
        self.current_site = None
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Setup event handlers"""

        @self.cloner.on_start
        def on_start(data):
            self.current_site = {
                "url": data.url,
                "start_time": datetime.now().isoformat(),
                "status": "in_progress"
            }
            print(f"\n{'='*60}")
            print(f"Cloning: {data.url}")
            print(f"{'='*60}")

        @self.cloner.on_complete
        def on_complete(data):
            if self.current_site:
                self.current_site.update({
                    "status": "success",
                    "end_time": datetime.now().isoformat(),
                    "duration": data.duration_seconds,
                    "output_path": data.output_path,
                    "statistics": {
                        "total": data.total_resources,
                        "success": data.successful_downloads,
                        "failed": data.failed_downloads,
                        "skipped": data.skipped_downloads
                    }
                })
                self.results.append(self.current_site)

            print(f"✅ Success: {data.successful_downloads}/{data.total_resources} files")

        @self.cloner.on_error
        def on_error(data):
            if self.current_site:
                self.current_site.update({
                    "status": "error",
                    "end_time": datetime.now().isoformat(),
                    "error": data.error
                })
                self.results.append(self.current_site)

            print(f"❌ Error: {data.error}")

        @self.cloner.on_progress
        def on_progress(data):
            bar_length = 40
            filled = int(bar_length * data.percentage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r[{bar}] {data.percentage:5.1f}% - {data.stage:<20}", end="", flush=True)

    def clone_websites(self, urls: list) -> dict:
        """
        Clone multiple websites

        Args:
            urls: List of website URLs to clone

        Returns:
            Dictionary with results summary
        """
        print(f"\n🚀 Starting batch clone of {len(urls)} websites...\n")

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            try:
                self.cloner.clone(url)
            except Exception as e:
                print(f"Failed to clone {url}: {e}")
                continue

        # Generate summary
        summary = self.generate_summary()
        self.save_report(summary)

        return summary

    def generate_summary(self) -> dict:
        """Generate summary of batch cloning results"""
        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = sum(1 for r in self.results if r["status"] == "error")

        total_duration = sum(r.get("duration", 0) for r in self.results if "duration" in r)
        total_downloads = sum(
            r.get("statistics", {}).get("success", 0) for r in self.results
        )

        return {
            "total_sites": len(self.results),
            "successful": success_count,
            "failed": error_count,
            "total_duration_seconds": total_duration,
            "total_downloads": total_downloads,
            "results": self.results
        }

    def save_report(self, summary: dict):
        """Save batch cloning report to JSON file"""
        report_path = Path("cloned_sites") / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\n📄 Report saved to: {report_path}")

    def print_summary(self, summary: dict):
        """Print summary to console"""
        print(f"\n{'='*60}")
        print("BATCH CLONE SUMMARY")
        print(f"{'='*60}")
        print(f"Total sites: {summary['total_sites']}")
        print(f"✅ Successful: {summary['successful']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏱️  Total time: {summary['total_duration_seconds']:.2f}s")
        print(f"📦 Total downloads: {summary['total_downloads']}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # List of websites to clone
    websites = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
    ]

    # Create batch cloner
    batch = BatchCloner(headless=True)

    # Clone all websites
    summary = batch.clone_websites(websites)

    # Print summary
    batch.print_summary(summary)

    print("\n🎉 Batch cloning complete!")
