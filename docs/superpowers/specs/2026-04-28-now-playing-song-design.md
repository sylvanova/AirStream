# Now-Playing Song Display — Design

**Date:** 2026-04-28
**Status:** Approved, ready for implementation plan

## Goal

Show the currently playing song on top of the station that's playing, on both desktop (PySide6) and mobile (Flutter). The current behavior only shows the station name.

## Acceptance criteria

### Desktop
- When a station is playing and stream metadata is available, the play button's accessible name reads `"Pause, now playing <song> on <station>"`. Tabbing onto the button announces this through the screen reader.
- When metadata is not available, the accessible name falls back to `"Pause, now playing <station>"`.
- The visible "Now playing:" label next to the play button mirrors the same info: `"Now playing: <song> — <station>"` (or just `"Now playing: <station>"` when no song is known). Sighted users see it too.
- The visible button caption stays `"Play"` / `"Pause"` — long song titles are *only* in the accessible name, not on the button face.
- When paused: button accessible name is `"Play, <station> paused"`; label reads `"<station> — paused"`. No song info, since playback isn't current.
- Song changes during playback do **not** trigger a screen-reader announcement (would be too noisy). The new song is silently picked up; the next time the user tabs onto the play button, the new title is read.

### Mobile
- The bottom now-playing bar shows the song title (top line, larger/bold) and the station name (bottom line, smaller/dim). When no song is known, the bar collapses to a single station-name line (same height as today).
- The Android system media notification (lockscreen, Bluetooth display, connected devices) updates with `MediaItem(title: <song>, artist: <station>)` whenever a new song is detected. When no song is known, it falls back to `MediaItem(title: <station>, artist: <country>)` — today's behavior.
- The bar's `semanticsLabel` matches the desktop format: `"Now playing: <song> on <station>"` or `"Now playing: <station>"`.

## Non-goals

- Custom album art / station logos. Out of scope.
- A history view of previously played songs. Out of scope.
- Shazam-style audio fingerprinting. Out of scope; we only use what the stream broadcasts.
- A separate "what's playing now" keyboard shortcut. Out of scope (the play button's accessible name already carries it; users can re-Tab to hear it).

## Architecture

A single new piece of state per platform: **`current_song`** (a string, possibly empty), owned by the audio layer. It's emitted on a stream/signal whenever stream metadata reports a new title. The UI subscribes and re-renders the play button + now-playing label/bar.

When the station changes or playback stops, `current_song` is cleared.

## Metadata source

We use **ICY/Shoutcast metadata** — the only universal standard for in-stream song titles on internet radio. The acquisition strategy differs per platform:

- **Mobile:** `just_audio.AudioPlayer.icyMetadataStream` is reliable and well-supported. Native only.
- **Desktop:** Qt's `QMediaPlayer.metaDataChanged` is best-effort (coverage varies by multimedia backend). We try native first, and if no metadata arrives within 8 seconds of starting playback, we open a side-channel HTTP request with `Icy-MetaData: 1` to parse `StreamTitle` ourselves. The fallback closes when the station changes or playback stops.

A custom ICY parser is **not** added on mobile. If a station that the user actually relies on turns out to come up empty there, we'll revisit.

## Component design

### Desktop — `services/audio_player.py`

Add to `AudioPlayer`:

- `song_changed = Signal(str)` — emitted with the trimmed, deduplicated title (or empty string to clear).
- Subscribe to `self._player.metaDataChanged` and read `Title` (`QMediaMetaData.Title`) from the player's `metaData()`. If non-empty and changed from `_last_song`, store and emit.
- On `play(url)`: emit `song_changed("")` to reset; start an 8-second `QTimer`.
- If `metaDataChanged` produces a non-empty Title before the timer fires, cancel the timer.
- If the timer fires with no native metadata, start an `IcyMetadataReader` worker (see below).
- On `stop()` or a new `play(url)`: emit `song_changed("")`, cancel the timer, stop the reader.

Add a private `IcyMetadataReader` helper:

- A `QThread`-driven worker that opens a `urllib` request to the stream URL with `Icy-MetaData: 1`.
- Reads the `icy-metaint` response header to determine the metadata interval.
- In a loop: reads `icy-metaint` audio bytes (and discards them), then reads the metadata block (1 byte length × 16, then that many bytes), parses `StreamTitle='...';`, emits a Qt signal back to the main thread when the title changes.
- Stop signal closes the socket and exits the loop. Errors silently terminate the reader (we keep the station playing; we just don't get song titles).

### Desktop — `app/player_controls.py`

- New instance state `_current_song: str = ""`.
- New private method `_refresh_labels()` — single source of truth that recomputes the play button's accessible name and the now-playing label text from `(_last_state, _current_station, _current_song)`.
- The three places that currently set those texts (`play_station`, `_on_state_changed`, plus the new `_on_song_changed`) all delegate to `_refresh_labels()`.
- `_on_song_changed(song)` updates `_current_song` and calls `_refresh_labels()`. **No `announce()` call.**
- `_player.song_changed.connect(self._on_song_changed)` in `__init__`.
- `MainWindow._on_stop` already stops the player, which will emit `""`; the existing label reset stays.

**Format table (single source of truth in `_refresh_labels`):**

| State | Visible button | Button accessible name | Visible label |
|---|---|---|---|
| no station, or stopped | `Play` | `Play` | `Not playing` |
| buffering / playing, no song | `Pause` | `Pause, now playing <station>` | `Now playing: <station>` |
| playing, with song | `Pause` | `Pause, now playing <song> on <station>` | `Now playing: <song> — <station>` |
| paused | `Play` | `Play, <station> paused` | `<station> — paused` |
| error | `Play` | `Play` | `Playback error` |

`stopped` is treated identically to "no station" even when `_current_station` is still set in memory — once playback ended, there's nothing currently playing. `buffering` is treated like `playing` so the button shows Pause as soon as the user presses Play, instead of staying on "Play" until the stream is ready.

We track the last state in `PlayerControls` (the audio layer already emits it via `state_changed`) so `_refresh_labels` can pick the right row without needing extra context.

### Mobile — `services/audio_service.dart`

Add to `AudioPlayerHandler`:

- A `StreamController<String>.broadcast()` exposed as `Stream<String> get currentSongStream`.
- A `String _currentSong = ''` field.
- In the constructor, subscribe to `_player.icyMetadataStream`. On each event:
  - Read `event?.info?.title?.trim() ?? ''`.
  - If unchanged, ignore.
  - Update `_currentSong` and add to `currentSongStream`.
  - Re-emit `mediaItem.add(MediaItem(id: <urlResolved>, title: <song or station.name>, artist: <station.name if song else country>))` — so the Android notification updates.
- In `playStation(station)`: set `_currentSong = ''`, emit `''` on `currentSongStream`, set the initial `MediaItem` with `title: station.name, artist: station.country` (today's behavior).
- In `stop()`: same clear.

### Mobile — `screens/home_screen.dart` (now-playing bar, lines 414–460)

Replace the single-line `Text(_currentStation!.name, ...)` inside the existing `StreamBuilder<PlayerState>` with a nested `StreamBuilder<String>` over `currentSongStream`. The inner builder renders:

- A `Column(crossAxisAlignment: CrossAxisAlignment.start, children: [...])` with:
  - Top line, **only when song is non-empty**: `Text(song, style: titleSmall (bold), overflow: ellipsis)`
  - Bottom line, always: `Text(station.name, style: bodySmall (dim), overflow: ellipsis)`
- The `Column` is wrapped in a `Semantics` with `label: "Now playing: <song> on <station>"` (or `"Now playing: <station>"` when no song), and the inner `Text`s use `excludeSemantics: true` so the screen reader reads the parent label, not both lines independently.
- The `mainAxisSize: MainAxisSize.min` on the column and the song line being conditional means the bar collapses to its previous height when no song is known.

The play/pause icon button to the right is unchanged.

## Data flow

```
Stream metadata (ICY)
        │
        ▼
┌─────────────────────────┐
│  AudioPlayer            │   QMediaPlayer.metaDataChanged
│  (desktop)              │   ─────► song_changed Signal
│  IcyMetadataReader      │   (fallback after 8s)
└─────────────────────────┘
        │ song string
        ▼
┌─────────────────────────┐
│  PlayerControls         │   _on_song_changed → _refresh_labels()
│  ───────────────►       │   button.accessibleName, label.text
└─────────────────────────┘

────────────── mobile ──────────────

just_audio.icyMetadataStream
        │  IcyMetadata.info.title
        ▼
┌─────────────────────────┐
│  AudioPlayerHandler     │   ─► currentSongStream (UI)
│                         │   ─► mediaItem.add(...) (Android system)
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  HomeScreen now-playing │   StreamBuilder<String>
│  bar                    │   two-line column + Semantics label
└─────────────────────────┘
```

## Error handling

- **No metadata broadcast by the station:** silent fallback to station-name-only labels. Already covered by the empty-string path.
- **ICY parser fails on desktop** (network error, malformed headers, weird encoding): worker logs at debug level and exits; the user keeps hearing audio but doesn't get song titles. No UI error shown — the absence of a song line is the signal.
- **Title encoding:** ICY metadata is conventionally Latin-1 but many stations send UTF-8. The parser tries UTF-8 first, falls back to Latin-1 with `errors='replace'`.
- **Rapid title changes during retuning:** the dedup check on `_last_song` / `_currentSong` swallows duplicates. We don't try to debounce — the station decides cadence.

## Testing

- **Desktop unit:** mock `QMediaPlayer.metaData()` to return varying titles, assert `song_changed` is emitted only when the title actually changes and only when non-empty.
- **Desktop unit:** mock the format-table inputs `(state, station, song)` against `_refresh_labels()` outputs; one test per row of the format table.
- **Desktop ICY parser unit:** feed the reader a fake byte stream with known `icy-metaint` and `StreamTitle` blocks; assert it emits the expected sequence of titles. Cover UTF-8, Latin-1, no-title-change, and empty-title cases.
- **Mobile unit:** mock `icyMetadataStream`, push events, assert `currentSongStream` emits the right values and `mediaItem` is updated.
- **Mobile widget:** pump the home screen with a fake handler, push song events, assert the bar shows two lines vs. one, and the `Semantics` label is correct.
- **Manual smoke (both platforms):** play a station known to broadcast metadata (most major web radios do), confirm song updates within ~10s of tuning. Play a station that doesn't, confirm fallback. Pause/resume/stop transitions match the format table.

## Out-of-scope follow-ups

- ICY parser fallback on mobile (only if a real station fails native).
- Album art via `IcyHeaders.url` if present.
- A "song history" panel.
