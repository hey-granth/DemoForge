"""DemoForge CLI — generate demo videos from the command line.

Usage:
    demoforge <url>
    demoforge <url> --output demo.mp4
    demoforge <url> --viewport 1920x1080
    demoforge setup
"""

import argparse
import asyncio
import shutil
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

import demoforge


def _print_status(msg: str) -> None:
    """Print a progress message to stderr."""
    print(f"  → {msg}", file=sys.stderr, flush=True)


def _parse_viewport(value: str) -> tuple[int, int]:
    """Parse a viewport string like '1280x720' into (width, height)."""
    try:
        parts = value.lower().split("x")
        if len(parts) != 2:
            raise ValueError
        w, h = int(parts[0]), int(parts[1])
        if w <= 0 or h <= 0:
            raise ValueError
        return w, h
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(
            f"Invalid viewport '{value}'. Expected format: WIDTHxHEIGHT (e.g. 1280x720)"
        )


def _validate_url(url: str) -> str:
    """Validate and normalise the target URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise argparse.ArgumentTypeError(f"Invalid URL: {url}")
    return url


def _check_dependencies() -> None:
    """Verify that required system tools are available."""
    if shutil.which("ffmpeg") is None:
        print(
            "Error: ffmpeg is not installed or not on PATH.\n"
            "Install it with your system package manager:\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  macOS:         brew install ffmpeg\n"
            "  Windows:       choco install ffmpeg",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(
            "Error: playwright is not installed.\n"
            "Install it with: pip install playwright",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_browsers() -> None:
    """Verify that Playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.launch(headless=True)
            browser.close()
        finally:
            pw.stop()
    except Exception:
        print(
            "Error: Playwright Chromium browser is not installed.\n"
            "Run: demoforge setup",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_setup() -> None:
    """Install Playwright Chromium browser."""
    import subprocess

    print("Installing Playwright Chromium browser…", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=False,
    )
    if result.returncode != 0:
        print("Failed to install Chromium.", file=sys.stderr)
        sys.exit(1)

    print("Installing system dependencies for Chromium…", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install-deps", "chromium"],
        capture_output=False,
    )
    if result.returncode != 0:
        print(
            "Failed to install system dependencies.\n"
            "You may need to run this command with sudo.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Setup complete.", file=sys.stderr)


def cmd_record(args: argparse.Namespace) -> None:
    """Execute the recording pipeline."""
    from demoforge.core.pipeline import run_demo_pipeline

    url = _validate_url(args.url)
    viewport_w, viewport_h = _parse_viewport(args.viewport)
    output = Path(args.output).resolve()

    print(f"DemoForge v{demoforge.__version__}", file=sys.stderr)
    print(f"Target:   {url}", file=sys.stderr)
    print(f"Viewport: {viewport_w}x{viewport_h}", file=sys.stderr)
    print(f"Output:   {output}", file=sys.stderr)
    print(file=sys.stderr)

    gemini_key = os.getenv("GEMINI_API_KEY")

    try:
        result = asyncio.run(
            run_demo_pipeline(
                url,
                output,
                viewport_width=viewport_w,
                viewport_height=viewport_h,
                max_clicks=args.max_clicks,
                max_depth=args.max_depth,
                max_runtime=args.max_runtime,
                gemini_api_key=gemini_key,
                on_status=_print_status,
            )
        )
        print(file=sys.stderr)
        print(f"✓ Video saved to {result}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except FileNotFoundError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demoforge",
        description="Generate automated demo videos of websites.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"demoforge {demoforge.__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- setup ---
    subparsers.add_parser(
        "setup",
        help="Install Playwright Chromium browser and system dependencies.",
    )

    # --- record (default) ---
    record_parser = subparsers.add_parser(
        "record",
        help="Record a demo video of a website.",
    )
    _add_record_args(record_parser)

    # Also allow `demoforge <url>` without the `record` subcommand
    _add_record_args(parser)

    return parser


def _add_record_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "url",
        nargs="?",
        help="Target website URL to record.",
    )
    parser.add_argument(
        "-o", "--output",
        default="demo.mp4",
        help="Output file path (default: demo.mp4).",
    )
    parser.add_argument(
        "--viewport",
        default="1280x720",
        help="Browser viewport as WIDTHxHEIGHT (default: 1280x720).",
    )
    parser.add_argument(
        "--max-clicks",
        type=int,
        default=10,
        help="Maximum interactions to perform (default: 10).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum navigation depth (default: 3).",
    )
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=300,
        help="Maximum execution time in seconds (default: 300).",
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Handle subcommand dispatch
    if args.command == "setup":
        cmd_setup()
        return

    if args.command == "record" or args.url:
        if not args.url:
            parser.error("url is required")
        _check_dependencies()
        _check_browsers()
        cmd_record(args)
        return

    # No arguments — print help
    parser.print_help(sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()

