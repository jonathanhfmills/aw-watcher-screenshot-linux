"""Data types and models for the screenshot watcher."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class CaptureMode(Enum):
    """Screenshot capture modes."""

    FULL = "full"
    CROP = "crop"


class ImageFormat(Enum):
    """Supported image formats."""

    PNG = "png"
    JPEG = "jpg"


@dataclass
class BoundingBox:
    """Window bounding box coordinates."""

    left: int
    top: int
    right: int
    bottom: int

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to tuple (L, T, R, B)."""
        return (self.left, self.top, self.right, self.bottom)

    def to_list(self) -> list[int]:
        """Convert to list [L, T, R, B]."""
        return [self.left, self.top, self.right, self.bottom]

    @property
    def width(self) -> int:
        """Calculate width."""
        return self.right - self.left

    @property
    def height(self) -> int:
        """Calculate height."""
        return self.bottom - self.top


@dataclass
class WindowInfo:
    """Information about an active window."""

    title: str = ""
    app: Optional[str] = None
    pid: Optional[int] = None
    win_id: Optional[int] = None
    bbox: Optional[BoundingBox] = None

    def get_key(self) -> Tuple[Optional[int], Optional[str], str]:
        """Get unique identifier for window state comparison."""
        return (self.win_id, self.app, self.title)


@dataclass
class WatcherConfig:
    """Configuration for the screenshot watcher."""

    poll_interval: float
    crop_to_window: bool
    capture_on_start: bool
    screenshots_dir: Path
    spool_dir: Optional[Path]
    image_format: ImageFormat
    jpeg_quality: int
    testing_mode: bool
    log_level: str
    min_screenshot_interval: float
    screenshot_delay: float
    screen_number: int
    detect_window_info: bool  # Whether to detect window info at all

    def __post_init__(self):
        """Ensure directories exist and validate config."""
        self.screenshots_dir = Path(self.screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        if self.spool_dir:
            self.spool_dir = Path(self.spool_dir)
            self.spool_dir.mkdir(parents=True, exist_ok=True)

        # If window detection is disabled, force crop off
        if not self.detect_window_info:
            self.crop_to_window = False
