# aw-watcher-screenshot-linux

ActivityWatch watcher that captures screenshots on window changes. **Linux-only**, Wayland-native — works on COSMIC, wlroots compositors, GNOME, and X11.

Forked from [Srakai/aw-watcher-screenshot](https://github.com/Srakai/aw-watcher-screenshot). The upstream supported macOS and Windows but was broken on Wayland. This fork drops cross-platform support and focuses on Linux with native Wayland capture, perceptual dedup, and disk management.

## How it works

1. Polls for window changes via the ActivityWatch API (reads from your running `aw-watcher-window` instance)
2. On window change, waits 5s then captures a screenshot via your compositor's native tool
3. Computes a perceptual hash (dHash) — skips the screenshot if the screen looks the same
4. Saves as WebP (3x smaller than PNG) and emits an ActivityWatch event with app, title, path, and hash
5. Cleans up old screenshots when count or disk limits are exceeded

## Screenshot backends

Detected automatically in order:

| Backend | Compositor | Notes |
|---------|-----------|-------|
| `cosmic-screenshot` | COSMIC | Silent capture, no portal needed |
| `grim` | wlroots (Sway, Hyprland, etc.) | |
| `gnome-screenshot` | GNOME | |

## Installation

```bash
pip install .
# or
uv pip install .
```

### NixOS

A Nix package and systemd user service are provided in the author's dotfiles. See `dotfiles/pkgs/aw-watcher-screenshot-linux/default.nix`.

## Usage

```bash
# Default: WebP, window detection via AW API, 5s delay, 5000 file / 2GB limit
aw-watcher-screenshot-linux

# Debug mode
aw-watcher-screenshot-linux --log-level DEBUG

# JPEG output, lower quality
aw-watcher-screenshot-linux --format jpg --quality 50

# Tighter limits
aw-watcher-screenshot-linux --max-screenshots 1000 --max-disk-mb 500

# No window detection (timer-only mode — not very useful)
aw-watcher-screenshot-linux --no-window-detection --capture-on-start
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--format` | `webp` | Image format: `webp`, `jpg`, `png` |
| `--quality` | `70` | WebP/JPEG quality (1-100) |
| `--poll` | `1.0` | Polling interval in seconds |
| `--screenshot-delay` | `5.0` | Seconds to wait after window change |
| `--min-interval` | `5.0` | Minimum seconds between screenshots |
| `--max-screenshots` | `5000` | Max files to keep (0=unlimited) |
| `--max-disk-mb` | `2000` | Max disk usage in MB (0=unlimited) |
| `--hash-threshold` | `4` | dHash distance threshold for dedup |
| `--screens-dir` | `~/.local/share/activitywatch/screenshots` | Screenshot directory |
| `--testing` | off | AW testing mode |

## Dependencies

- `aw-client`, `aw-core` — ActivityWatch integration
- `click` — CLI
- `pillow` — Image format conversion
- `imagehash` — Perceptual hashing (dHash)
- `requests` — AW API queries for window detection
- One of: `cosmic-screenshot`, `grim`, `gnome-screenshot` — screenshot capture

## Limitations

The ActivityWatch web UI has no built-in screenshot viewer. Screenshots are stored as events in the `aw-watcher-screenshot-linux_{hostname}` bucket with file paths, but the UI only shows raw event metadata in the Raw Data tab. There's no timeline scrubbing with inline screenshots like ManicTime offers.

What you get today:
- Screenshots saved to disk as `.webp` files (`~/.local/share/activitywatch/screenshots/`)
- Events in AW with `app`, `title`, `path`, and `phash` fields — queryable via the API
- Perceptual dedup prevents redundant captures

What's missing (would require an AW web UI plugin):
- Inline screenshot gallery on the timeline
- Scrubbing the timeline to see what was on screen at any point
- Thumbnail previews in event lists

## Future

- [ ] Rust rewrite — single static binary, no Python runtime
- [ ] ActivityWatch web UI plugin for screenshot timeline visualization

## License

MIT
