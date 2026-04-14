# AirStream

A simple, accessible internet radio player. Browse thousands of stations, play them with one keypress, and save your favorites. Available on Desktop (Windows, macOS, Linux) and Android.

## Features

- Automatically loads popular stations from [Radio Browser](https://www.radio-browser.info/)
- Filter by country, genre, or search by name
- Favorite stations and add custom ones
- Full screen reader support: NVDA, VoiceOver, Orca, TalkBack
- Follows system dark/light theme

## Download

Grab the latest build from [Releases](../../releases).

- **Windows**: `AirStream.exe` — standalone, no install needed
- **macOS**: `AirStream.dmg` — drag to Applications
- **Linux**: `AirStream` — standalone binary
- **Android**: `AirStream.apk` — install directly on your phone

## Desktop Keyboard Shortcuts

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

## Android Accessibility (TalkBack)

- Swipe to navigate stations
- Double-tap to play
- Two-finger double-tap (magic tap) to play/pause
- Swipe up/down on a station for "Add to favorites" action
- Filter dialogs are fully navigable

## Run from Source

**Desktop (Python):**
```
pip install -r requirements.txt
python main.py
```

**Android (Flutter):**
```
cd mobile
flutter pub get
flutter run
```

## Build

**Desktop:**
```
pip install -r requirements.txt
python build.py           # auto-detects platform
python build.py windows   # or: macos, linux
```

**Android:**
```
cd mobile
flutter build apk --release
```

## License

MIT
