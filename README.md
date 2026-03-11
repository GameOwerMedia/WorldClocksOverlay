# World Clock Overlay

Transparent always-on-top world clock overlay for Windows, built with Python and PySide6.

World Clock Overlay is a lightweight desktop utility for people who need additional clocks without a heavy dashboard. It can run as a compact horizontal line near the taskbar clock, or as multiple detached clock windows placed anywhere across one or more monitors.

## Screenshot

![World Clock Overlay line window preview](docs/screenshots/line-window.png)

## Highlights

- Transparent, frameless, always-on-top clock widgets
- Two layout modes:
  - `Line window` for multiple clocks in one horizontal strip
  - `Separate window` for independent movable clocks
- Searchable, scrollable city picker
- Unlimited clocks
- Per-clock window position and size persistence
- Mouse drag to move
- Mouse wheel scaling
- Rounded corners and translucent themes
- Tray icon with quick show/hide controls
- Configurable `24h / 12h` format and seconds
- Local timezone support via `zoneinfo` and `tzdata`
- Windows autostart support
- PyInstaller packaging to a standalone `.exe`

## Why This Project

Windows only gives you limited timezone visibility near the system clock. This project provides a compact open-source alternative that stays visually lightweight while still being flexible enough for multi-monitor setups, travel workflows, and distributed teams.

## Requirements

- Windows
- Python 3.11+

## Stack

- Python
- PySide6
- `zoneinfo`
- `tzdata`
- PyInstaller

## Quick Start

1. Install Python 3.11 or newer.
2. Open the project folder.
3. Run:

```bat
install.bat
```

4. Launch:

```bat
dist\WorldClockOverlay.exe
```

For development mode:

```bat
run_dev.bat
```

## Build Output

The packaged executable is generated at:

```text
dist\WorldClockOverlay.exe
```

## How It Works

Each city can be assigned one of three modes:

- `Off`
- `Line window`
- `Separate window`

This lets you mix both workflows:

- keep a compact horizontal strip near the taskbar
- open selected clocks as standalone floating windows

## Controls

- Left mouse button: move a clock window
- Mouse wheel: scale the active window
- Bottom-right grip: resize the active window
- Right click: open the context menu
- Tray icon click: show / hide all clocks

## Context Menu

- `Add or remove clocks...`
- `Show / Hide seconds`
- `Switch 24h / 12h`
- `Reload config`
- `Theme: Black`
- `Theme: White`
- `Snap to bottom-right`
- `Save position`
- `Close this clock`
- `Exit`

## Tray Menu

- `Show all clocks`
- `Hide all clocks`
- `Add or remove clocks...`
- `Reload config`
- `Theme: Black`
- `Theme: White`
- `Exit`

## Configuration

The app uses a local `config.json` stored next to the source files, or next to the executable after build.

You can configure:

- active cities
- line vs separate window placement
- opacity
- 24h / 12h format
- seconds visibility
- theme
- saved window positions and sizes

Example:

```json
{
  "display": {
    "show_seconds": false,
    "use_24h": true,
    "theme": "black"
  }
}
```

Available theme values:

- `"black"`
- `"white"`

## Autostart

`install.bat` can register the app for the current Windows user in:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

`uninstall.bat` removes that entry.

## Repository Files

- `app.py` - main application
- `config.json` - local configuration
- `requirements.txt` - Python dependencies
- `run_dev.bat` - development run
- `build.bat` - manual EXE build
- `install.bat` - venv setup, dependencies, build, optional autostart
- `uninstall.bat` - remove Windows autostart
- `README.md` - English documentation
- `README.pl.md` - Polish documentation
- `LICENSE` - MIT license

## Notes

- This project does not hook into the native Windows taskbar clock area.
- It is intentionally implemented as floating overlays instead of a shell extension.
- Clock functionality does not require internet access.

## License

Released under the MIT License. See `LICENSE`.
