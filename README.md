# World Clock Overlay

A lightweight, transparent world clock overlay for Windows.

Sits near your taskbar or floats anywhere across your monitors. Built with Python and PySide6, packaged as a single standalone `.exe`.

![World Clock Overlay preview](docs/screenshots/line-window.png)

## Features

- Transparent, frameless, always-on-top widgets
- Two layout modes: horizontal **line strip** or independent **floating windows**
- 100+ cities across all major timezones
- Searchable city picker with per-clock placement control
- Mouse drag to move, scroll to scale, corner grip to resize
- Per-window position and size persistence across sessions
- System tray with show/hide toggle
- Dark and light translucent themes
- 24h/12h format and optional seconds display
- Works fully offline using local timezone data

## Quick Start

**Requirements:** Windows, Python 3.11+

```bat
install.bat
```

Then launch:

```bat
dist\WorldClockOverlay.exe
```

For development:

```bat
run_dev.bat
```

## Controls

| Input | Action |
|---|---|
| Left click + drag | Move window |
| Mouse wheel | Scale up/down |
| Bottom-right grip | Resize |
| Right click | Context menu |
| Tray icon click | Show/hide all clocks |

## Configuration

The app stores settings in `config.json` next to the executable (or source files in dev mode). All changes made through the UI are saved automatically.

You can also edit the file directly:

```json
{
  "window": {
    "opacity": 0.82,
    "always_on_top": true
  },
  "display": {
    "show_seconds": false,
    "use_24h": true,
    "theme": "black"
  }
}
```

Themes: `"black"`, `"white"`

## How It Works

Each city can be set to one of three modes:

- **Off** - not displayed
- **Line window** - added to the shared horizontal strip
- **Separate window** - independent floating clock

Mix both modes freely. Use the line strip for a compact taskbar companion, and separate windows for clocks you want on specific monitors.

## Project Structure

| File | Purpose |
|---|---|
| `app.py` | Application source |
| `config.json` | Default configuration |
| `requirements.txt` | Python dependencies |
| `install.bat` | Build environment setup and EXE packaging |
| `build.bat` | Standalone build script |
| `run_dev.bat` | Run from source |
| `uninstall.bat` | Cleanup script |

## Stack

- Python 3.11+
- PySide6
- `zoneinfo` + `tzdata`
- PyInstaller

## Notes

- This is a floating overlay, not a native taskbar extension.
- All timezone data is local. No network access required.

## License

MIT License. See [LICENSE](LICENSE).
