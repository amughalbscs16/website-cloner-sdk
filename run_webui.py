#!/usr/bin/env python
"""
Convenience script to run the FastAPI Web UI

Usage:
    python run_webui.py
    python run_webui.py --host 0.0.0.0 --port 8000
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web import run_server


def main():
    parser = argparse.ArgumentParser(
        description="WordPress Website Cloner - Web UI"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("WordPress Website Cloner - Web UI")
    print("=" * 60)
    print(f"\nStarting server on http://{args.host}:{args.port}")
    print(f"   Local:    http://127.0.0.1:{args.port}")
    if args.host == "0.0.0.0":
        print(f"   Network:  http://<your-ip>:{args.port}")
    print("\nTips:")
    print("   - Enter any website URL to clone it")
    print("   - View cloned websites in the preview iframe")
    print("   - Manage your cloned projects in the history section")
    print("\nPress CTRL+C to stop the server\n")

    try:
        run_server(host=args.host, port=args.port, reload=args.reload)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)


if __name__ == "__main__":
    main()
