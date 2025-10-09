#!/usr/bin/env python3
"""CLI entry point for aw-watcher-screenshot."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from aw_watcher_screenshot.models import ImageFormat, WatcherConfig
from aw_watcher_screenshot.utils import FileUtils
from aw_watcher_screenshot.watcher import ScreenshotWatcher

LOG = logging.getLogger("aw-watcher-screenshot")


@click.command()
@click.option(
    "--poll",
    "poll_time",
    type=float,
    default=1.0,
    show_default=True,
    help="Polling interval in seconds.",
)
@click.option(
    "--no-window-detection",
    is_flag=True,
    default=False,
    help="Disable window detection (fast mode - screenshot only).",
)
@click.option(
    "--crop-active-window",
    is_flag=True,
    default=False,
    help="Crop screenshot to active window bounds (requires window detection).",
)
@click.option(
    "--capture-on-start",
    is_flag=True,
    default=False,
    show_default=True,
    help="Capture immediately on startup.",
)
@click.option(
    "--screens-dir",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    default=None,
    help="Directory to save screenshots.",
)
@click.option(
    "--spool-dir",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    default=None,
    help="Directory to write JSON records for external LLM processing.",
)
@click.option(
    "--jpeg",
    "use_jpeg",
    is_flag=True,
    default=False,
    help="Save as JPEG instead of PNG (requires Pillow).",
)
@click.option(
    "--quality",
    type=int,
    default=90,
    show_default=True,
    help="JPEG quality (1-100) if --jpeg is set.",
)
@click.option(
    "--min-interval",
    type=float,
    default=5.0,
    show_default=True,
    help="Minimum seconds between screenshots (rate limiting).",
)
@click.option(
    "--screenshot-delay",
    type=float,
    default=5.0,
    show_default=True,
    help="Seconds to wait after window change before capturing.",
)
@click.option(
    "--screen",
    type=int,
    default=1,
    show_default=True,
    help="Which screen to capture (1=first screen, 0=all screens).",
)
@click.option(
    "--testing",
    is_flag=True,
    default=False,
    help="ActivityWatch client testing mode.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Logging level.",
)
def main(
    poll_time: float,
    no_window_detection: bool,
    crop_active_window: bool,
    capture_on_start: bool,
    screens_dir: Optional[str],
    spool_dir: Optional[str],
    use_jpeg: bool,
    quality: int,
    min_interval: float,
    screenshot_delay: float,
    screen: int,
    testing: bool,
    log_level: str,
):
    """
    ActivityWatch screenshot watcher.

    Captures screenshots on window change (or on a timer in fast mode).

    \b
    Fast Mode (--no-window-detection):
      - No window detection overhead
      - Screenshots on timer only
      - Best performance

    \b
    Window Detection Mode (default):
      - Detects window changes
      - Captures app/title metadata
      - Optional cropping support
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Build configuration
    config = WatcherConfig(
        poll_interval=poll_time,
        crop_to_window=crop_active_window,
        capture_on_start=capture_on_start,
        screenshots_dir=(
            Path(screens_dir) if screens_dir else FileUtils.get_default_screenshot_dir()
        ),
        spool_dir=Path(spool_dir) if spool_dir else None,
        image_format=ImageFormat.JPEG if use_jpeg else ImageFormat.PNG,
        jpeg_quality=quality,
        testing_mode=testing,
        log_level=log_level,
        min_screenshot_interval=min_interval,
        screenshot_delay=screenshot_delay,
        screen_number=screen,
        detect_window_info=not no_window_detection,
    )

    LOG.info("=" * 60)
    LOG.info("ActivityWatch Screenshot Watcher")
    LOG.info("=" * 60)
    LOG.info(
        f"Mode: {'Fast (screenshot-only)' if no_window_detection else 'Window detection'}"
    )
    LOG.info(f"Screenshots: {config.screenshots_dir}")
    LOG.info(f"Screen: {screen} ({'all' if screen == 0 else 'single'})")
    LOG.info(f"Format: {config.image_format.value.upper()}")
    LOG.info(f"Min interval: {min_interval}s")
    LOG.info(f"Screenshot delay: {screenshot_delay}s")
    if crop_active_window:
        LOG.info("Cropping: Enabled")
    LOG.info("=" * 60)

    # Create and start watcher
    try:
        watcher = ScreenshotWatcher(config)
        watcher.start()
    except KeyboardInterrupt:
        LOG.info("Exiting on user interrupt.")
        sys.exit(0)
    except Exception as e:
        LOG.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
