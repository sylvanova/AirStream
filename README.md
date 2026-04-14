# AirStream

A simple, accessible internet radio player. Browse thousands of stations, play them with one keypress, and save your favorites.

## Features

- Automatically loads popular stations from [Radio Browser](https://www.radio-browser.info/)
- Filter by country, genre, or search by name
- Favorite stations and add custom ones
- Keyboard-first design with full screen reader support (NVDA, VoiceOver, Orca)

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Play station / activate button / open filter |
| Space | Play / Pause |
| Ctrl+P | Play / Pause |
| Ctrl+F | Focus search bar |
| Ctrl+B | Toggle favorite |
| Ctrl+L | View favorites |
| Ctrl+N | Add custom station |
| Ctrl+Up/Down | Volume up/down |
| Escape | Stop playback |
| Tab / Shift+Tab | Navigate between controls |
| Arrow keys | Navigate station list / filter options |

## Download

Grab the latest build from [Releases](../../releases) or the [Actions](../../actions) tab.

- **Windows**: `AirStream.exe` — standalone, no install needed
- **macOS**: `AirStream.dmg` — drag to Applications

## Run from Source

```
pip install -r requirements.txt
python main.py
```

## Build

```
pip install -r requirements.txt
python build.py           # auto-detects platform
python build.py windows   # or: macos, linux
```

## License

MIT
