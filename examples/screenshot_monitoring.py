"""Example: Screenshot monitoring and continuous capture"""

import asyncio
from pathlib import Path
from src.monitors import monitor_website, ScreenshotScheduler
from src.drivers.chrome_driver import ChromeDriverManager


async def example_basic_monitoring():
    """Example: Basic continuous monitoring"""
    print("Example 1: Basic Monitoring (5 captures, 1 minute interval)")
    print("=" * 60)

    stats = await monitor_website(
        url="https://example.com",
        output_dir=Path("./monitoring_output"),
        interval_minutes=1,  # Capture every 1 minute
        max_captures=5,      # Stop after 5 captures
        viewports=None,      # Full-page only
        headless=True
    )

    print("\nMonitoring Complete!")
    print(f"Total Captures: {stats['total_captures']}")
    print(f"Successful: {stats['successful_captures']}")
    print(f"Failed: {stats['failed_captures']}")
    print(f"Duration: {stats['duration_seconds']:.0f} seconds")


async def example_multi_viewport_monitoring():
    """Example: Monitoring with multiple viewports"""
    print("\nExample 2: Multi-Viewport Monitoring")
    print("=" * 60)

    stats = await monitor_website(
        url="https://example.com",
        output_dir=Path("./monitoring_output_multi"),
        interval_minutes=2,
        max_captures=3,
        viewports=["mobile", "desktop"],  # Capture both mobile and desktop
        headless=True
    )

    print("\nMonitoring Complete!")
    print(f"Total Captures: {stats['total_captures']}")
    print(f"Viewports per capture: 2 (mobile + desktop)")


async def example_with_callback():
    """Example: Monitoring with callback on each capture"""
    print("\nExample 3: Monitoring with Callback")
    print("=" * 60)

    driver_manager = ChromeDriverManager(headless=True)
    driver = driver_manager.create_driver()

    try:
        driver.get("https://example.com")
        await asyncio.sleep(2)

        scheduler = ScreenshotScheduler(
            driver,
            output_dir=Path("./monitoring_output_callback"),
            interval_seconds=30,  # 30 seconds
            max_captures=3
        )

        # Register callback
        @scheduler.on_capture
        def handle_capture(screenshot_path, capture_number):
            print(f"  📸 Capture #{capture_number} saved: {screenshot_path}")

        stats = await scheduler.start_monitoring(
            url="https://example.com",
            page_name="main",
            fullpage=True
        )

        print("\nMonitoring Complete!")
        print(f"All screenshots saved to: ./monitoring_output_callback/screenshots/")

    finally:
        driver_manager.close()


async def example_duration_based():
    """Example: Monitor for a specific duration"""
    print("\nExample 4: Duration-Based Monitoring (2 hours)")
    print("=" * 60)

    stats = await monitor_website(
        url="https://example.com",
        output_dir=Path("./monitoring_output_duration"),
        interval_minutes=10,   # Every 10 minutes
        duration_hours=2,      # Run for 2 hours
        max_captures=None,     # No capture limit
        headless=True
    )

    print("\nMonitoring Complete!")
    print(f"Ran for: {stats['duration_seconds'] / 3600:.1f} hours")
    print(f"Total Captures: {stats['total_captures']}")


async def main():
    """Run all examples"""
    print("Screenshot Monitoring Examples")
    print("=" * 60)
    print("This demonstrates various monitoring scenarios.\n")

    # Run basic example
    await example_basic_monitoring()

    # Uncomment to run other examples:
    # await example_multi_viewport_monitoring()
    # await example_with_callback()
    # await example_duration_based()

    print("\n" + "=" * 60)
    print("Examples complete! Check the output directories for screenshots.")


if __name__ == "__main__":
    asyncio.run(main())
