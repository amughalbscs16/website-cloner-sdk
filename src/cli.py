"""Enhanced CLI with monitoring commands"""

import sys
import asyncio
import argparse
from pathlib import Path
from .cloner import clone_website
from .monitors import monitor_website
from .utils.logger import logger, setup_logger
from .config import config


def create_parser():
    """Create argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        description="WordPress Website Cloner - Clone and monitor websites",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global arguments
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path"
    )

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Clone command
    clone_parser = subparsers.add_parser(
        "clone",
        help="Clone a website once",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli clone https://example.com
  python -m src.cli clone https://example.com --visible
  python -m src.cli clone https://example.com --no-screenshots
        """
    )

    clone_parser.add_argument("url", help="Website URL to clone")
    clone_parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    clone_parser.add_argument("--output", type=Path, help="Output directory")
    clone_parser.add_argument("--no-screenshots", action="store_true", help="Disable screenshot capture")

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Continuously monitor a website with scheduled screenshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli monitor https://example.com
  python -m src.cli monitor https://example.com --interval 10
  python -m src.cli monitor https://example.com --captures 24 --interval 60
  python -m src.cli monitor https://example.com --duration 2 --viewports mobile,desktop
        """
    )

    monitor_parser.add_argument("url", help="Website URL to monitor")
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Minutes between captures (default: 5)"
    )
    monitor_parser.add_argument(
        "--captures",
        type=int,
        help="Maximum number of captures (default: unlimited)"
    )
    monitor_parser.add_argument(
        "--duration",
        type=int,
        help="Maximum monitoring duration in hours (default: unlimited)"
    )
    monitor_parser.add_argument(
        "--viewports",
        help="Comma-separated list of viewports (e.g., mobile,desktop,tablet)"
    )
    monitor_parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode"
    )
    monitor_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory"
    )

    return parser


async def run_monitor(args):
    """Run monitoring command"""
    logger.info(f"Starting monitoring: {args.url}")
    logger.info(f"Interval: {args.interval} minutes")

    if args.output:
        config.PROJECT_DIR = args.output
        config.PROJECT_DIR.mkdir(exist_ok=True, parents=True)

    # Parse viewports
    viewports = None
    if args.viewports:
        viewports = [v.strip() for v in args.viewports.split(",")]
        logger.info(f"Viewports: {viewports}")

    # Create output directory for this URL
    from .utils.file_utils import FileManager
    file_manager = FileManager(config.PROJECT_DIR)
    output_dir = file_manager.create_project_directory(args.url)

    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Screenshots will be saved in: {output_dir}/screenshots/")

    # Run monitoring
    stats = await monitor_website(
        url=args.url,
        output_dir=output_dir,
        interval_minutes=args.interval,
        max_captures=args.captures,
        duration_hours=args.duration,
        viewports=viewports,
        headless=not args.visible
    )

    # Print final statistics
    print("\n" + "=" * 60)
    print("MONITORING SESSION COMPLETE")
    print("=" * 60)
    print(f"Total Captures:      {stats['total_captures']}")
    print(f"Successful:          {stats['successful_captures']}")
    print(f"Failed:              {stats['failed_captures']}")
    print(f"Success Rate:        {stats['success_rate']:.1f}%")
    if stats['duration_seconds']:
        print(f"Duration:            {stats['duration_seconds']:.0f} seconds")
    print(f"Output Directory:    {output_dir}")
    print(f"Screenshots Folder:  {output_dir}/screenshots/")
    print("=" * 60)

    return 0 if stats['failed_captures'] == 0 else 1


def run_clone(args):
    """Run clone command"""
    if args.output:
        config.PROJECT_DIR = args.output
        config.PROJECT_DIR.mkdir(exist_ok=True, parents=True)

    if args.no_screenshots:
        config.ENABLE_SCREENSHOTS = False

    headless = not args.visible
    output_path = clone_website(args.url, headless=headless)

    print(f"\n✓ Website cloned successfully!")
    print(f"Location: {output_path}")
    print(f"Open: {output_path / 'index.html'}")

    if config.ENABLE_SCREENSHOTS:
        print(f"Screenshots: {output_path / 'screenshots'}")

    return 0


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logger(log_file=args.log_file, level=log_level)

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "clone":
            return run_clone(args)

        elif args.command == "monitor":
            # Run async monitor command
            return asyncio.run(run_monitor(args))

        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        logger.warning("\nCancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
