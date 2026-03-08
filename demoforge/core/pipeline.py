"""Standalone demo recording pipeline.

This module provides the core recording function used by both the CLI tool
and the Redis-backed worker. It encapsulates the full sequence: launch browser,
discover interactions, plan actions, execute demo, close browser, convert video.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Optional, Callable

from playwright.async_api import Error as PlaywrightError

from demoforge.core.browser import BrowserSession
from demoforge.core.discovery import InteractionDiscovery
from demoforge.core.planner import InteractionPlanner
from demoforge.core.executor import ExecutionController
from demoforge.core.recorder import VideoProcessor


async def run_demo_pipeline(
    url: str,
    output_path: Path,
    *,
    viewport_width: int = 1280,
    viewport_height: int = 720,
    max_clicks: int = 10,
    max_depth: int = 3,
    max_runtime: int = 300,
    gemini_api_key: Optional[str] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> Path:
    """Run the full demo recording pipeline and return the path to the final MP4.

    Parameters
    ----------
    url:
        Target website URL.
    output_path:
        Destination file path for the generated MP4.
    viewport_width:
        Browser viewport width in pixels.
    viewport_height:
        Browser viewport height in pixels.
    max_clicks:
        Maximum number of interactions to perform.
    max_depth:
        Maximum navigation depth.
    max_runtime:
        Maximum wall-clock execution time in seconds.
    gemini_api_key:
        Optional Gemini API key for LLM-based interaction ranking.
    on_status:
        Optional callback invoked with progress messages.

    Returns
    -------
    Path
        Absolute path to the generated MP4 file.

    Raises
    ------
    RuntimeError
        If the pipeline fails at any stage.
    FileNotFoundError
        If ffmpeg or the recorded video cannot be found.
    """

    def _emit(msg: str) -> None:
        if on_status is not None:
            on_status(msg)

    temp_dir = Path(tempfile.mkdtemp(prefix="demoforge_"))
    video_dir = temp_dir / "raw"
    video_dir.mkdir(exist_ok=True)

    browser: Optional[BrowserSession] = None

    try:
        # 1. Launch browser
        _emit("Launching browser…")
        browser = BrowserSession(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            video_dir=video_dir,
        )
        await browser.start()

        if not browser.page:
            raise RuntimeError("Browser page failed to initialize")

        # 2. Navigate and execute interactions
        _emit(f"Navigating to {url}…")
        discovery = InteractionDiscovery(browser.page)
        planner = InteractionPlanner(api_key=gemini_api_key)
        executor = ExecutionController(
            max_clicks=max_clicks,
            max_depth=max_depth,
            max_runtime=max_runtime,
        )

        _emit("Recording interactions…")
        await executor.execute_demo(url, browser, discovery, planner)

        # 3. Close browser to flush video
        _emit("Finalizing recording…")
        await browser.stop()
        browser = None  # prevent double-close in finally

        # 4. Discover and convert video
        _emit("Converting to MP4…")
        processor = VideoProcessor()
        raw_video = processor.discover_video_file(video_dir)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_video = processor.process_video(raw_video, output_path)

        # 5. Validate
        if not final_video.exists():
            raise RuntimeError("Final MP4 file was not created")
        if final_video.stat().st_size == 0:
            raise RuntimeError("Generated video is empty (0 bytes)")

        _emit(f"Saved to {final_video}")
        return final_video

    finally:
        # Clean up browser if still open
        if browser is not None:
            try:
                await browser.stop()
            except PlaywrightError:
                pass

        # Remove raw recording scratch directory
        if video_dir.exists():
            try:
                shutil.rmtree(video_dir, ignore_errors=True)
            except OSError:
                pass


