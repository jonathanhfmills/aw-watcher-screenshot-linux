"""Window detection - optional and platform-specific.

This module is completely optional. If not used, the watcher will simply
capture screenshots on a timer without detecting window changes.
"""

import logging
import subprocess
from typing import Optional, Protocol

import psutil

from .models import BoundingBox, WindowInfo

LOG = logging.getLogger(__name__)


class WindowDetector(Protocol):
    """Protocol for platform-specific window detection."""

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        ...


class WindowsWindowDetector:
    """Windows-specific window detection."""

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get active window information on Windows."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            # Get title
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value or ""

            # Get PID
            pid_value = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_value))
            pid = int(pid_value.value)

            # Get app name
            app = None
            try:
                app = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                LOG.debug(f"Could not get process name for PID {pid}")

            # Get window rect (optional, only if needed for cropping)
            bbox = None
            try:

                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG),
                    ]

                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                bbox = BoundingBox(
                    left=int(rect.left),
                    top=int(rect.top),
                    right=int(rect.right),
                    bottom=int(rect.bottom),
                )
            except Exception:
                pass  # bbox remains None

            return WindowInfo(
                title=title,
                app=app,
                pid=pid,
                win_id=int(hwnd),
                bbox=bbox,
            )
        except Exception as e:
            LOG.debug(f"Windows active window detection failed: {e}")
            return None


class MacOSWindowDetector:
    """macOS-specific window detection."""

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get active window information on macOS."""
        try:
            from AppKit import NSWorkspace
            import Quartz

            workspace = NSWorkspace.sharedWorkspace()
            app_obj = workspace.frontmostApplication()
            if not app_obj:
                return None

            pid = int(app_obj.processIdentifier())
            app_name = str(app_obj.localizedName())

            # Basic info is enough for fast operation
            win_id = None
            title = ""
            bbox = None

            # Only get window details if we need them (slower)
            try:
                options = (
                    Quartz.kCGWindowListOptionOnScreenOnly
                    | Quartz.kCGWindowListExcludeDesktopElements
                )
                window_list = (
                    Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
                    or []
                )

                # Find the frontmost window for this app
                for window in window_list:
                    if int(window.get("kCGWindowOwnerPID", -1)) != pid:
                        continue
                    if int(window.get("kCGWindowLayer", 0)) != 0:
                        continue

                    title = window.get("kCGWindowName", "") or ""
                    bounds = window.get("kCGWindowBounds", {}) or {}

                    x = int(bounds.get("X", 0))
                    y = int(bounds.get("Y", 0))
                    width = int(bounds.get("Width", 0))
                    height = int(bounds.get("Height", 0))

                    bbox = BoundingBox(
                        left=x,
                        top=y,
                        right=x + width,
                        bottom=y + height,
                    )
                    win_id = int(window.get("kCGWindowNumber", 0))
                    break
            except Exception:
                pass  # bbox and win_id remain None

            return WindowInfo(
                title=title,
                app=app_name,
                pid=pid,
                win_id=win_id,
                bbox=bbox,
            )
        except Exception as e:
            LOG.debug(f"macOS active window detection failed: {e}")
            return None


class LinuxWindowDetector:
    """Linux-specific window detection (X11)."""

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get active window information on Linux."""
        # Try xlib first, then fallback to shell commands
        return self._try_xlib() or self._try_shell_commands()

    def _try_xlib(self) -> Optional[WindowInfo]:
        """Try to get window info using python-xlib and ewmh."""
        try:
            from Xlib import X
            from ewmh import EWMH

            ewmh = EWMH()
            window = ewmh.getActiveWindow()
            if not window:
                return None

            title = ewmh.getWmName(window) or ""
            wm_class = window.get_wm_class()
            app = wm_class[0] if wm_class else None

            # Get PID
            pid_prop = window.get_full_property(
                ewmh.display.get_atom("_NET_WM_PID"), X.AnyPropertyType
            )
            pid = int(pid_prop.value[0]) if pid_prop else None

            # Get geometry (optional)
            bbox = None
            try:
                geom = window.get_geometry()
                bbox = BoundingBox(
                    left=int(geom.x),
                    top=int(geom.y),
                    right=int(geom.x + geom.width),
                    bottom=int(geom.y + geom.height),
                )
            except Exception:
                pass

            return WindowInfo(
                title=title,
                app=app,
                pid=pid,
                win_id=int(window.id),
                bbox=bbox,
            )
        except Exception:
            return None

    def _try_shell_commands(self) -> Optional[WindowInfo]:
        """Fallback: use xdotool/xprop shell commands."""
        try:
            # Get active window ID
            wid_str = (
                subprocess.check_output(
                    ["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL
                )
                .decode()
                .strip()
            )
            wid = int(wid_str, 10)

            # Get window title
            title = (
                subprocess.check_output(
                    ["xdotool", "getwindowname", str(wid)], stderr=subprocess.DEVNULL
                )
                .decode()
                .rstrip()
            )

            # Get PID
            pid = None
            try:
                pid_output = subprocess.check_output(
                    ["xprop", "-id", str(wid), "_NET_WM_PID"], stderr=subprocess.DEVNULL
                ).decode()
                pid = int(pid_output.strip().split()[-1])
            except Exception:
                pass

            # Get app name from /proc if we have PID
            app = None
            if pid:
                try:
                    with open(f"/proc/{pid}/comm", "r") as f:
                        app = f.read().strip()
                except Exception:
                    pass

            # Get geometry (optional, only if needed)
            bbox = None
            try:
                geom_output = subprocess.check_output(
                    ["xdotool", "getwindowgeometry", "--shell", str(wid)],
                    stderr=subprocess.DEVNULL,
                ).decode()

                geom_dict = {}
                for line in geom_output.splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        geom_dict[key.strip()] = value.strip()

                x = int(geom_dict.get("X", 0))
                y = int(geom_dict.get("Y", 0))
                width = int(geom_dict.get("WIDTH", 0))
                height = int(geom_dict.get("HEIGHT", 0))

                bbox = BoundingBox(left=x, top=y, right=x + width, bottom=y + height)
            except Exception:
                pass

            return WindowInfo(
                title=title,
                app=app,
                pid=pid,
                win_id=wid,
                bbox=bbox,
            )
        except Exception:
            return None


def get_window_detector() -> Optional[WindowDetector]:
    """
    Get the appropriate window detector for the current platform.

    Returns None if window detection is not available or fails.
    """
    import platform

    try:
        system = platform.system()

        if system == "Windows":
            return WindowsWindowDetector()
        elif system == "Darwin":
            return MacOSWindowDetector()
        else:  # Linux
            return LinuxWindowDetector()
    except Exception as e:
        LOG.warning(f"Could not initialize window detector: {e}")
        return None
