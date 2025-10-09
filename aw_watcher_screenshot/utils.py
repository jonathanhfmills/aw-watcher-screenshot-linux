"""Utility functions for file operations and time handling."""

import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


class FileUtils:
    """Utilities for file operations."""

    _SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")

    @staticmethod
    def sanitize_filename(text: str, max_length: int = 64) -> str:
        """Sanitize text for use in filenames."""
        if not text:
            return "unknown"

        text = text.strip().replace(" ", "-")
        text = FileUtils._SANITIZE_RE.sub("-", text)
        text = re.sub(r"-{2,}", "-", text).strip("-")
        return text[:max_length] or "x"

    @staticmethod
    def write_atomic(path: Path, data: bytes) -> None:
        """Write file atomically using temp file and rename."""
        temp_path = path.with_suffix(f".tmp.{uuid.uuid4().hex}")
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(path)
        except Exception:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    @staticmethod
    def get_default_screenshot_dir() -> Path:
        """Get platform-specific default screenshot directory."""
        import platform

        system = platform.system()
        home = Path.home()

        if system == "Windows":
            base = (
                Path(os.getenv("LOCALAPPDATA", home / "AppData" / "Local"))
                / "ActivityWatch"
                / "Screenshots"
            )
        elif system == "Darwin":
            base = (
                home
                / "Library"
                / "Application Support"
                / "ActivityWatch"
                / "Screenshots"
            )
        else:  # Linux
            base = (
                Path(os.getenv("XDG_DATA_HOME", home / ".local" / "share"))
                / "activitywatch"
                / "screenshots"
            )

        base.mkdir(parents=True, exist_ok=True)
        return base


class TimeUtils:
    """Utilities for time operations."""

    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC time."""
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def to_filesystem_iso(dt: datetime) -> str:
        """Convert datetime to filesystem-friendly ISO format."""
        return dt.isoformat(timespec="milliseconds").replace(":", "-")

    @staticmethod
    def sleep_aligned(interval: float) -> None:
        """Sleep to align with wall clock intervals (stable cadence)."""
        now = time.time()
        sleep_duration = interval - (now % interval)

        # Clamp to valid range
        if sleep_duration < 0 or sleep_duration > interval:
            sleep_duration = max(0.0, min(interval, sleep_duration))

        time.sleep(sleep_duration)
