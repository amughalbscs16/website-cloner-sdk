"""Main entry point for the WordPress cloner application"""

import sys
import argparse
from pathlib import Path
from .cloner import clone_website
from .utils.logger import logger, setup_logger
from .config import config


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="WordPress Website Cloner - Clone websites locally with all assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --visible
  %(prog)s https://example.com --output ./cloned-sites
        """
    )

    parser.add_argument(
        "url",
        help="Website URL to clone"
    )

    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode (not headless)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for cloned websites (default: ./project)"
    )

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

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logger(log_file=args.log_file, level=log_level)

    # Update config if output specified
    if args.output:
        config.PROJECT_DIR = args.output
        config.PROJECT_DIR.mkdir(exist_ok=True, parents=True)

    try:
        # Clone the website
        headless = not args.visible
        output_path = clone_website(args.url, headless=headless)

        print(f"\n✓ Website cloned successfully!")
        print(f"Location: {output_path}")
        print(f"Open: {output_path / 'index.html'}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Failed to clone website: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
