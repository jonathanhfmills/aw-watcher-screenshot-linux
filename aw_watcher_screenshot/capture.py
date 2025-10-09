"""Screenshot capture functionality."""

import io
import logging
from typing import Optional, Tuple

from mss import mss
from mss.tools import to_png

from .models import BoundingBox, ImageFormat

LOG = logging.getLogger(__name__)


class ImageCapture:
    """Handles screenshot capture and encoding."""

    def __init__(
        self, image_format: ImageFormat, jpeg_quality: int = 90, screen_number: int = 1
    ):
        """
        Initialize image capture.

        Args:
            image_format: Output image format (PNG or JPEG)
            jpeg_quality: JPEG quality (1-100) if using JPEG format
            screen_number: Which screen to capture (1-indexed, 0 for all screens)
        """
        self.image_format = image_format
        self.jpeg_quality = jpeg_quality
        self.screen_number = screen_number
        self._pil_available = self._check_pil_available()

    def _check_pil_available(self) -> bool:
        """Check if PIL/Pillow is available for JPEG encoding."""
        if self.image_format == ImageFormat.PNG:
            return False

        try:
            from PIL import Image

            return True
        except ImportError:
            LOG.warning(
                "Pillow not installed; JPEG format unavailable. Using PNG instead."
            )
            self.image_format = ImageFormat.PNG
            return False

    def capture(
        self, region: Optional[BoundingBox] = None
    ) -> Tuple[bytes, ImageFormat]:
        """
        Capture screenshot and encode to specified format.

        Args:
            region: Optional bounding box to crop to. None for full screen.

        Returns:
            Tuple of (image_bytes, actual_format_used)
        """
        # Capture as PNG first
        png_bytes = self._capture_png(region)

        # Convert to JPEG if requested and available
        if self.image_format == ImageFormat.JPEG and self._pil_available:
            try:
                jpeg_bytes = self._convert_to_jpeg(png_bytes)
                return jpeg_bytes, ImageFormat.JPEG
            except Exception as e:
                LOG.error(f"JPEG encoding failed: {e}. Using PNG fallback.")
                return png_bytes, ImageFormat.PNG

        return png_bytes, ImageFormat.PNG

    def _capture_png(self, region: Optional[BoundingBox]) -> bytes:
        """Capture screenshot as PNG bytes."""
        with mss() as sct:
            if region:
                monitor = {
                    "left": max(0, region.left),
                    "top": max(0, region.top),
                    "width": max(1, region.width),
                    "height": max(1, region.height),
                }
                screenshot = sct.grab(monitor)
            else:
                # Capture specific screen or first screen (not virtual desktop)
                # screen_number: 0 = all screens (virtual), 1+ = specific screen
                if self.screen_number == 0:
                    # All screens (virtual desktop)
                    screenshot = sct.grab(sct.monitors[0])
                elif 1 <= self.screen_number <= len(sct.monitors) - 1:
                    # Specific screen (monitors[0] is virtual, monitors[1+] are physical)
                    screenshot = sct.grab(sct.monitors[self.screen_number])
                else:
                    # Default to first physical screen if out of range
                    LOG.warning(
                        f"Screen {self.screen_number} not found. "
                        f"Using screen 1. Available screens: {len(sct.monitors) - 1}"
                    )
                    screenshot = sct.grab(sct.monitors[1])

            buffer = io.BytesIO()
            buffer.write(to_png(screenshot.rgb, screenshot.size))
            return buffer.getvalue()

    def _convert_to_jpeg(self, png_bytes: bytes) -> bytes:
        """Convert PNG bytes to JPEG."""
        from PIL import Image

        png_buffer = io.BytesIO(png_bytes)
        image = Image.open(png_buffer).convert("RGB")

        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format="JPEG", quality=self.jpeg_quality)
        return jpeg_buffer.getvalue()
