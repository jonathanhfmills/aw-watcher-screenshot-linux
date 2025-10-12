"""Main screenshot watcher implementation."""

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import aw_client
from aw_core import Event

from .capture import ImageCapture
from .models import CaptureMode, ImageFormat, WatcherConfig, WindowInfo
from .utils import FileUtils, TimeUtils
from .window_detector import get_window_detector

LOG = logging.getLogger(__name__)


class ScreenshotWatcher:
    """Main watcher class that coordinates screenshot capture."""

    def __init__(self, config: WatcherConfig):
        """
        Initialize screenshot watcher.

        Args:
            config: Watcher configuration
        """
        self.config = config

        # Optional window detector - can be None for fast mode
        self.window_detector = None
        if config.detect_window_info:
            self.window_detector = get_window_detector()
            if self.window_detector is None:
                LOG.warning(
                    "Window detection not available. "
                    "Running in screenshot-only mode."
                )

        self.image_capture = ImageCapture(
            config.image_format, config.jpeg_quality, config.screen_number
        )

        # Initialize ActivityWatch client
        self.client = aw_client.ActivityWatchClient(
            "aw-watcher-screenshot", testing=config.testing_mode
        )
        self.bucket_id = f"{self.client.client_name}_{self.client.client_hostname}"

        # State tracking
        self.last_window_key: Optional[Tuple] = None
        self.last_screenshot_time: Optional[datetime] = None
        self.pending_window_change: Optional[Tuple[datetime, WindowInfo]] = None

    def start(self) -> None:
        """Start the watcher main loop."""
        LOG.info(
            f"Starting screenshot watcher "
            f"(poll={self.config.poll_interval}s, "
            f"window_detection={self.window_detector is not None}, "
            f"crop={self.config.crop_to_window})"
        )

        # Connect to ActivityWatch
        self.client.wait_for_start()
        self.client.connect()
        self.client.create_bucket(self.bucket_id, "app.screenshot")

        # Initial capture if configured
        if self.config.capture_on_start:
            if self.window_detector:
                window_info = self.window_detector.get_active_window()
                if window_info:
                    self.last_window_key = window_info.get_key()
                    self._capture_and_emit(window_info)
            else:
                # No window detection, just capture
                self._capture_and_emit(None)

        # Main loop
        self._run_loop()

    def _run_loop(self) -> None:
        """Main polling loop."""
        while True:
            start_time = TimeUtils.now_utc()

            # Get current window (if window detection is enabled)
            window_info = None
            if self.window_detector:
                window_info = self.window_detector.get_active_window()
                LOG.debug(
                    f"Current window: {window_info.get_key() if window_info else None}"
                )

            # Check if window changed
            current_key = window_info.get_key() if window_info else None
            window_changed = (
                current_key != self.last_window_key and window_info is not None
            )

            if window_changed:
                LOG.info(f"Window changed: {self.last_window_key} -> {current_key}")
                # Schedule screenshot after delay
                self.pending_window_change = (start_time, window_info)
                self.last_window_key = current_key

            # Check if we should capture a pending screenshot
            if self.pending_window_change:
                change_time, pending_info = self.pending_window_change
                time_since_change = (start_time - change_time).total_seconds()

                LOG.debug(
                    f"Pending screenshot - time since change: {time_since_change:.1f}s (delay: {self.config.screenshot_delay}s)"
                )

                # Check if delay has passed and minimum interval is respected
                if time_since_change >= self.config.screenshot_delay:
                    should_capture = True

                    # Enforce minimum screenshot interval
                    if self.last_screenshot_time:
                        time_since_last = (
                            start_time - self.last_screenshot_time
                        ).total_seconds()
                        if time_since_last < self.config.min_screenshot_interval:
                            should_capture = False
                            LOG.debug(
                                f"Skipping screenshot - too soon since last "
                                f"({time_since_last:.1f}s < {self.config.min_screenshot_interval}s)"
                            )

                    if should_capture:
                        LOG.debug(
                            f"Capturing screenshot for {pending_info.app if pending_info else 'unknown'}"
                        )
                        self._capture_and_emit(pending_info)
                        self.last_screenshot_time = start_time
                        self.pending_window_change = None

            # Sleep until next poll
            TimeUtils.sleep_aligned(self.config.poll_interval)

    def _capture_and_emit(self, window_info: Optional[WindowInfo]) -> None:
        """Capture screenshot and emit event."""
        timestamp = TimeUtils.now_utc()

        # Determine capture mode and region
        capture_mode = CaptureMode.FULL
        region = None

        if self.config.crop_to_window and window_info and window_info.bbox:
            capture_mode = CaptureMode.CROP
            region = window_info.bbox

        # Capture screenshot
        try:
            image_bytes, image_format = self.image_capture.capture(region)
        except Exception as e:
            LOG.error(f"Screenshot capture failed: {e}")
            return

        # Generate filename
        timestamp_str = TimeUtils.to_filesystem_iso(timestamp)
        app_name = window_info.app if window_info else "unknown"
        title = window_info.title if window_info else ""

        filename = (
            f"{timestamp_str}_"
            f"{FileUtils.sanitize_filename(app_name)}_"
            f"{FileUtils.sanitize_filename(title)}"
            f".{image_format.value}"
        )
        filepath = self.config.screenshots_dir / filename

        # Write file
        try:
            FileUtils.write_atomic(filepath, image_bytes)
        except Exception as e:
            LOG.error(f"Failed to write screenshot: {e}")
            return

        # Calculate hash
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        # Create ActivityWatch event with all screenshot data
        event_data = {
            # "title": window_info.title if window_info else "",
            # "app": window_info.app if window_info else None,
            # "pid": window_info.pid if window_info else None,
            # "win_id": window_info.win_id if window_info else None,
            # "bbox": (
            #    window_info.bbox.to_list() if window_info and window_info.bbox else None
            # ),
            "path": str(filepath.absolute()),
            "reason": "window_title_change" if window_info else "timer",
            "capture": {
                "mode": capture_mode.value,
                "hash_sha256": image_hash,
            },
        }

        event = Event(
            timestamp=timestamp,
            duration=timedelta(seconds=0),
            data=event_data,
        )

        try:
            self.client.insert_event(self.bucket_id, event)
            LOG.info(f"Captured {app_name} ({title}) -> {filepath.name}")
        except Exception as e:
            LOG.error(f"Failed to insert ActivityWatch event: {e}")
