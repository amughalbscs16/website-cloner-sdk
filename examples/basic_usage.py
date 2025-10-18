"""
Basic usage example of the WordPress Cloner SDK

This example shows the simplest way to use the cloner with the convenience function.
"""

from src import clone_website, ProgressData, CloneCompleteData


def on_progress(data: ProgressData):
    """Handle progress updates"""
    print(f"[{data.percentage:5.1f}%] {data.message}")


def on_complete(data: CloneCompleteData):
    """Handle completion"""
    print(f"\n✅ Clone complete!")
    print(f"   Output: {data.output_path}")
    print(f"   Duration: {data.duration_seconds:.2f}s")
    print(f"   Downloads: {data.successful_downloads} successful, {data.failed_downloads} failed")


if __name__ == "__main__":
    # Clone a website with callbacks
    output = clone_website(
        "https://example.com",
        headless=True,
        on_progress=on_progress,
        on_complete=on_complete
    )

    print(f"\nCloned website saved to: {output}")
