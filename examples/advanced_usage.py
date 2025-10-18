"""
Advanced usage example with decorator-based event handling

This example shows how to use decorators for cleaner event handling.
"""

from src import ClonerSDK


# Create SDK instance
cloner = ClonerSDK(headless=True)

# Use decorators to subscribe to events


@cloner.on_start
def handle_start(data):
    """Called when cloning starts"""
    print(f"🚀 Starting clone: {data.url}")
    print(f"   Headless mode: {data.headless}")


@cloner.on_progress
def handle_progress(data):
    """Called on each progress update"""
    # Create a progress bar
    bar_length = 30
    filled = int(bar_length * data.percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r[{bar}] {data.percentage:5.1f}% - {data.message[:50]:<50}", end="", flush=True)


@cloner.on_page_loaded
def handle_page_loaded(data):
    """Called when the page is fully loaded"""
    print(f"\n📄 Page loaded successfully")


@cloner.on_network_logs_extracted
def handle_network_logs(data):
    """Called when network logs are extracted"""
    print(f"🌐 Found {data.total_resources} resources in network logs")


@cloner.on_resource_downloaded
def handle_resource_downloaded(data):
    """Called for each successful download"""
    # Optional: Track specific resources
    if data.file_type in ['css', 'js']:
        print(f"\n  ✓ {data.file_type.upper()}: {data.url[:80]}")


@cloner.on_resource_failed
def handle_resource_failed(data):
    """Called when a resource download fails"""
    print(f"\n  ✗ Failed: {data.url}")
    if data.error:
        print(f"    Error: {data.error}")


@cloner.on_stats_update
def handle_stats(data):
    """Called when statistics are updated"""
    # You could push these stats to a dashboard, database, etc.
    pass


@cloner.on_complete
def handle_complete(data):
    """Called when cloning is complete"""
    print(f"\n\n✅ Clone complete!")
    print(f"   URL: {data.url}")
    print(f"   Output: {data.output_path}")
    print(f"   Duration: {data.duration_seconds:.2f}s")
    print(f"\n📊 Statistics:")
    print(f"   Total resources: {data.total_resources}")
    print(f"   ✓ Success: {data.successful_downloads}")
    print(f"   ✗ Failed: {data.failed_downloads}")
    print(f"   ⊘ Skipped: {data.skipped_downloads}")


@cloner.on_error
def handle_error(data):
    """Called if an error occurs"""
    print(f"\n❌ Error: {data.error}")
    if data.traceback:
        print(f"\nTraceback:\n{data.traceback}")


if __name__ == "__main__":
    # Clone a website
    try:
        output_path = cloner.clone("https://example.com")
        print(f"\n🎉 Success! Website saved to: {output_path}")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
