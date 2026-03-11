# World Clock Overlay

A compact transparent always-on-top world clock overlay for Windows.

World Clock Overlay is a lightweight desktop widget system for Windows. It supports multiple independent clock windows that can be placed anywhere on any monitor, along with tray integration, searchable city selection, editable time zones, compact resizing, Windows autostart, and two translucent themes for dark and bright backgrounds.

## Features

- Frameless transparent overlay window
- Always on top
- Rounded corners
- System tray icon with show/hide support
- Left-click drag to move the widget
- Resize grip in the bottom-right corner
- Mouse wheel scaling
- Multiple independent clock windows
- Unlimited active clocks
- Searchable and scrollable city selection dialog
- Each clock can be moved and resized independently
- Clocks can be placed on different monitors
- City selection from the app menu
- Editable `config.json`
- Reload config without editing code
- Save window position and size
- Snap to bottom-right
- 24h / 12h toggle
- Seconds toggle
- Two translucent themes:
  - `Black` for bright screens
  - `White` for dark screens
- Windows autostart via `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- PyInstaller build to standalone EXE

## Requirements

- Windows
- Python 3.11+

## Tech Stack

- Python
- PySide6
- `zoneinfo`
- `tzdata`
- PyInstaller

## Project Files

- `app.py` - main application
- `config.json` - local configuration
- `requirements.txt` - Python dependencies
- `run_dev.bat` - run in development mode
- `build.bat` - build EXE manually
- `install.bat` - create venv, install dependencies, build EXE, optionally install autostart
- `uninstall.bat` - remove Windows autostart
- `README.md` - English project documentation
- `README.pl.md` - Polish documentation

## Quick Start

1. Install Python 3.11 or newer.
2. Open this project folder.
3. Run:

```bat
install.bat
```

4. After the build is complete, launch:

```bat
dist\WorldClockOverlay.exe
```

For development mode, run:

```bat
run_dev.bat
```

## Build Output

The packaged executable is created here:

```text
dist\WorldClockOverlay.exe
```

## Usage

- Left mouse button: drag the overlay
- Mouse wheel: scale the widget
- Bottom-right grip: resize the widget
- Right click: open the context menu
- Tray icon click: show / hide all clocks

## Context Menu

- `Select clocks...`
- `Show / Hide seconds`
- `Switch 24h / 12h`
- `Reload config`
- `Snap to bottom-right`
- `Theme: Black`
- `Theme: White`
- `Save position`
- `Close this clock`
- `Exit`

## Tray Menu

- `Show all`
- `Hide all`
- `Select clocks...`
- `Reload config`
- `Theme: Black`
- `Theme: White`
- `Exit`

## Configuration

The app uses a local `config.json` file next to the source files, or next to the EXE after build.

You can:

- enable or disable cities
- change opacity
- change time format
- toggle seconds
- choose the default theme
- keep or disable snap-to-corner behavior
- store independent position and size for each clock

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

## Notes

- The app does not integrate into the native Windows taskbar clock area.
- It is a floating overlay system meant to visually behave like one or more additional taskbar-adjacent clock widgets.
- Time zone data is local and does not require internet access.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
