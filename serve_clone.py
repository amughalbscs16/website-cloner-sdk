#!/usr/bin/env python
"""
Serve a cloned site over HTTP so it renders faithfully.

Browsers restrict file:// pages (opaque origin): web fonts, ES modules, and
cross-origin stylesheets are CORS-blocked, so double-clicking index.html can
look broken even when the clone is complete. Serving over HTTP fixes this.

Usage:
    python serve_clone.py project/<folder>        # serve a specific clone
    python serve_clone.py                          # list available clones
    python serve_clone.py project/<folder> --port 9000
"""

import argparse
import http.server
import functools
import sys
import webbrowser
from pathlib import Path


def list_clones(project_dir: Path):
    if not project_dir.exists():
        print(f"No project directory at {project_dir}")
        return
    clones = [d for d in project_dir.iterdir() if d.is_dir() and (d / "index.html").exists()]
    if not clones:
        print("No clones found. Clone a site first.")
        return
    import base64
    print("Available clones:\n")
    for d in clones:
        try:
            url = base64.b64decode(d.name).decode()
        except Exception:
            url = d.name
        print(f"  python serve_clone.py {d.as_posix()}")
        print(f"      ({url})\n")


def main():
    parser = argparse.ArgumentParser(description="Serve a cloned site over HTTP")
    parser.add_argument("path", nargs="?", help="Path to a clone directory")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--no-open", action="store_true", help="Don't open a browser")
    args = parser.parse_args()

    if not args.path:
        list_clones(Path("project"))
        return 0

    clone_dir = Path(args.path).resolve()
    if not (clone_dir / "index.html").exists():
        print(f"No index.html in {clone_dir}")
        return 1

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(clone_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}/index.html"
    print(f"Serving {clone_dir}\n  -> {url}\nPress Ctrl+C to stop.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
