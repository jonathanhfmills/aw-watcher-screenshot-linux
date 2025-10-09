# aw-watcher-screenshot

ActivityWatch watcher that captures screenshots on window changes.

## Features

- 📸 **Screenshot on window change** - Automatically captures when you switch windows
- ⚡ **Fast mode** - Optional `--no-window-detection` for minimal overhead
- 🖼️ **Single screen capture** - Captures only your primary screen (configurable)
- ⏱️ **Smart rate limiting** - Max 1 screenshot per 5 seconds by default
- ⏰ **Delay after change** - 5-second delay after window change (lets you settle in)
- 🎨 **PNG or JPEG** - Choose your preferred format
- ✂️ **Optional cropping** - Crop to active window bounds (when enabled)
- 📊 **ActivityWatch integration** - Stores metadata in AW database

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# macOS users (for window detection):
pip install pyobjc

# Linux users (for window detection):
pip install python-xlib ewmh

# Optional: for JPEG support
pip install Pillow
```

## Quick Start

### Fast Mode (Recommended)

Fastest performance, no window detection overhead:

```bash
python aw-watcher-screenshot.py --no-window-detection
```

### Window Detection Mode

Captures window metadata (app name, title):

```bash
python aw-watcher-screenshot.py
```

## Usage

```bash
# Basic usage (window detection enabled)
python aw-watcher-screenshot.py

# Fast mode (screenshot-only, no window detection)
python aw-watcher-screenshot.py --no-window-detection

# Capture all screens instead of just screen 1
python aw-watcher-screenshot.py --screen 0

# Use JPEG instead of PNG
python aw-watcher-screenshot.py --jpeg --quality 85

# Custom screenshot directory
python aw-watcher-screenshot.py --screens-dir ~/my-screenshots

# Faster screenshots (2 second intervals)
python aw-watcher-screenshot.py --min-interval 2.0 --screenshot-delay 2.0

# Enable cropping to active window
python aw-watcher-screenshot.py --crop-active-window
```

## Configuration Options

| Option                  | Default          | Description                              |
| ----------------------- | ---------------- | ---------------------------------------- |
| `--poll`                | 1.0              | Polling interval in seconds              |
| `--no-window-detection` | False            | Disable window detection (fast mode)     |
| `--crop-active-window`  | False            | Crop to active window bounds             |
| `--min-interval`        | 5.0              | Minimum seconds between screenshots      |
| `--screenshot-delay`    | 5.0              | Delay after window change before capture |
| `--screen`              | 1                | Which screen to capture (1=first, 0=all) |
| `--screens-dir`         | Platform default | Where to save screenshots                |
| `--jpeg`                | False            | Use JPEG instead of PNG                  |
| `--quality`             | 90               | JPEG quality (1-100)                     |
| `--testing`             | False            | Use AW testing mode                      |
| `--log-level`           | INFO             | Logging level                            |

## Project Structure

```
aw_watcher_screenshot/
├── __init__.py           # Package initialization
├── models.py            # Data types (WindowInfo, WatcherConfig, etc.)
├── utils.py             # File and time utilities
├── capture.py           # Screenshot capture logic
├── window_detector.py   # Platform-specific window detection (optional)
└── watcher.py          # Main watcher orchestration
```

## How It Works

1. **Window Detection Mode** (default):

   - Polls for active window every 1 second
   - Detects window changes (app name, title, etc.)
   - Waits 5 seconds after change (configurable)
   - Captures screenshot if 5+ seconds since last capture
   - Stores screenshot + metadata in ActivityWatch

2. **Fast Mode** (`--no-window-detection`):
   - No window detection overhead
   - Pure screenshot capture
   - Minimal CPU/memory usage
   - Still respects rate limiting

## Notes

- **Cropping is optional**: By default, cropping and bbox detection are disabled for speed
- **Single screen by default**: Captures only screen 1 (use `--screen 0` for all screens)
- **Rate limiting**: Maximum 1 screenshot per 5 seconds (prevents excessive captures)
- **Screenshot delay**: 5-second delay after window change gives you time to start working

## Platform Support

- ✅ **macOS**: Full support (requires `pyobjc` for window detection)
- ✅ **Windows**: Full support
- ✅ **Linux**: X11 support (requires `python-xlib ewmh` or `xdotool`)
- ⚠️ **Wayland**: Limited (no native window detection)

## Dependencies

### Core (required)

- `activitywatch-client` - ActivityWatch integration
- `mss` - Fast screenshot capture
- `psutil` - Process information
- `click` - CLI interface

### Platform-specific (optional, for window detection)

- **macOS**: `pyobjc`
- **Linux**: `python-xlib`, `ewmh` (or `xdotool` as fallback)
- **Windows**: Built-in (ctypes)

### Optional

- `Pillow` - JPEG encoding support

## License

Same as ActivityWatch (MPL-2.0)
