# Now-Playing Song Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the currently playing song alongside the station, on desktop (PySide6 button accessible name + visible label) and mobile (now-playing bar + Android system media notification).

**Architecture:** A single `current_song: str` lives in the audio layer per platform. Mobile uses `just_audio.icyMetadataStream` natively. Desktop tries `QMediaPlayer.metaDataChanged` first, falls back to a custom ICY parser worker if no metadata arrives within 8s. UI subscribes to a signal/stream and re-renders. A pure `format_labels()` function is the single source of truth for the desktop label/button strings.

**Tech Stack:** Python 3, PySide6 (QtMultimedia), pytest; Dart, Flutter, just_audio 0.9.x, audio_service 0.18.x, flutter_test.

**Spec:** `docs/superpowers/specs/2026-04-28-now-playing-song-design.md`

---

## File Structure

**Desktop — new files:**
- `services/icy_metadata_reader.py` — ICY parser worker (`QObject` running on a `QThread`)
- `services/now_playing_format.py` — pure functions that produce the desktop button/label strings
- `tests/__init__.py` — empty marker
- `tests/test_now_playing_format.py` — unit tests for the format functions
- `tests/test_icy_metadata_reader.py` — unit tests for the ICY byte parser
- `tests/test_audio_player_metadata.py` — unit tests for `AudioPlayer` metadata wiring (with mocked `QMediaPlayer`)
- `requirements-dev.txt` — pytest + pytest-mock

**Desktop — modified files:**
- `services/audio_player.py` — add `song_changed` signal, native + fallback metadata wiring
- `app/player_controls.py` — pull strings from `services/now_playing_format.py`, add `_on_song_changed`
- `app/main_window.py` — drop the redundant manual label reset in `_on_stop` (the player now drives it)

**Mobile — new files:**
- `mobile/test/audio_service_test.dart` — unit test for the new song-stream wiring
- `mobile/test/home_screen_bar_test.dart` — widget test for the two-line bar (covered if straightforward, otherwise manual)

**Mobile — modified files:**
- `mobile/lib/services/audio_service.dart` — `currentSongStream`, `icyMetadataStream` subscription, `MediaItem` re-emit
- `mobile/lib/screens/home_screen.dart` — replace single-line bar with a two-line `StreamBuilder<String>`

---

## Task 1: Add desktop test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create empty `tests/__init__.py`**

```python
```

(The file should be entirely empty.)

- [ ] **Step 3: Install dev requirements**

Run: `pip install -r requirements-dev.txt`
Expected: pytest and pytest-mock install successfully.

- [ ] **Step 4: Verify pytest discovers an empty suite**

Run: `pytest tests/ -v`
Expected: `no tests ran` (exit code 5 is OK here — the directory exists, no tests yet).

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt tests/__init__.py
git commit -m "Add pytest dev dependency and tests package"
```

---

## Task 2: Pure label-formatting functions (desktop)

**Files:**
- Create: `services/now_playing_format.py`
- Create: `tests/test_now_playing_format.py`

This isolates the format table from PySide6 so it can be tested without Qt. Both `PlayerControls` callers will import from here.

- [ ] **Step 1: Write the failing tests**

Write `tests/test_now_playing_format.py`:

```python
from services.now_playing_format import button_strings, label_string


def test_no_station():
    btn_visible, btn_a11y = button_strings(state="stopped", station=None, song="")
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert label_string(state="stopped", station=None, song="") == "Not playing"


def test_stopped_with_remembered_station_still_reads_as_idle():
    btn_visible, btn_a11y = button_strings(
        state="stopped", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert (
        label_string(state="stopped", station={"name": "Soma FM"}, song="")
        == "Not playing"
    )


def test_playing_no_song_yet():
    btn_visible, btn_a11y = button_strings(
        state="playing", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Soma FM"
    assert (
        label_string(state="playing", station={"name": "Soma FM"}, song="")
        == "Now playing: Soma FM"
    )


def test_buffering_treated_like_playing():
    btn_visible, btn_a11y = button_strings(
        state="buffering", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Soma FM"


def test_playing_with_song():
    btn_visible, btn_a11y = button_strings(
        state="playing", station={"name": "Soma FM"}, song="Tycho - A Walk"
    )
    assert btn_visible == "Pause"
    assert btn_a11y == "Pause, now playing Tycho - A Walk on Soma FM"
    assert (
        label_string(state="playing", station={"name": "Soma FM"}, song="Tycho - A Walk")
        == "Now playing: Tycho - A Walk — Soma FM"
    )


def test_paused_drops_song_info():
    btn_visible, btn_a11y = button_strings(
        state="paused", station={"name": "Soma FM"}, song="Tycho - A Walk"
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play, Soma FM paused"
    assert (
        label_string(state="paused", station={"name": "Soma FM"}, song="Tycho - A Walk")
        == "Soma FM — paused"
    )


def test_error_state():
    btn_visible, btn_a11y = button_strings(
        state="error", station={"name": "Soma FM"}, song=""
    )
    assert btn_visible == "Play"
    assert btn_a11y == "Play"
    assert (
        label_string(state="error", station={"name": "Soma FM"}, song="")
        == "Playback error"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_now_playing_format.py -v`
Expected: All tests fail with `ModuleNotFoundError: No module named 'services.now_playing_format'`.

- [ ] **Step 3: Write the implementation**

Create `services/now_playing_format.py`:

```python
"""Pure functions for the desktop now-playing button + label strings.

Single source of truth for the format table in the design spec
(docs/superpowers/specs/2026-04-28-now-playing-song-design.md).

State values mirror AudioPlayer.state_changed: "playing", "paused",
"stopped", "error", "buffering".
"""

from typing import Optional, Tuple

EM_DASH = "—"  # "—"


def _is_active(state: str) -> bool:
    """True for states where audio is meant to be coming out of the speakers."""
    return state in ("playing", "buffering")


def _station_name(station: Optional[dict]) -> str:
    if not station:
        return ""
    return station.get("name", "") or ""


def button_strings(
    state: str, station: Optional[dict], song: str
) -> Tuple[str, str]:
    """Return (visible_text, accessible_name) for the play/pause button."""
    name = _station_name(station)
    song = (song or "").strip()

    if state == "error":
        return "Play", "Play"

    if state == "stopped" or not name:
        return "Play", "Play"

    if state == "paused":
        return "Play", f"Play, {name} paused"

    # playing / buffering
    if song:
        return "Pause", f"Pause, now playing {song} on {name}"
    return "Pause", f"Pause, now playing {name}"


def label_string(state: str, station: Optional[dict], song: str) -> str:
    """Return the visible 'Now playing:' label text."""
    name = _station_name(station)
    song = (song or "").strip()

    if state == "error":
        return "Playback error"

    if state == "stopped" or not name:
        return "Not playing"

    if state == "paused":
        return f"{name} {EM_DASH} paused"

    # playing / buffering
    if song:
        return f"Now playing: {song} {EM_DASH} {name}"
    return f"Now playing: {name}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_now_playing_format.py -v`
Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/now_playing_format.py tests/test_now_playing_format.py
git commit -m "Add pure label-formatting functions for now-playing UI"
```

---

## Task 3: ICY metadata byte parser

**Files:**
- Create: `services/icy_metadata_reader.py` (parser only — Qt wiring comes in Task 4)
- Create: `tests/test_icy_metadata_reader.py`

The parser is the byte-level logic that reads `icy-metaint` blocks. It is split out as a pure generator so we can test it without sockets or threads.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_icy_metadata_reader.py`:

```python
import io

from services.icy_metadata_reader import (
    decode_metadata_block,
    parse_stream_title,
    iter_titles,
)


def _build_metadata_block(payload: bytes) -> bytes:
    """Encode a payload the way ICY does: 1 length byte (in 16-byte units), then padded payload."""
    length_units = (len(payload) + 15) // 16
    padded = payload.ljust(length_units * 16, b"\x00")
    return bytes([length_units]) + padded


def test_parse_stream_title_basic():
    assert parse_stream_title("StreamTitle='Tycho - A Walk';StreamUrl='';") == "Tycho - A Walk"


def test_parse_stream_title_no_title_returns_empty():
    assert parse_stream_title("StreamUrl='https://example.com';") == ""


def test_parse_stream_title_with_quotes_inside():
    # ICY uses single-quoted values; embedded quotes are rare but we accept the first ';' terminator.
    assert (
        parse_stream_title("StreamTitle='Hello, world';StreamUrl='';")
        == "Hello, world"
    )


def test_decode_metadata_block_utf8():
    raw = _build_metadata_block("StreamTitle='Björk - All Is Full of Love';".encode("utf-8"))
    assert decode_metadata_block(raw) == "Björk - All Is Full of Love"


def test_decode_metadata_block_latin1_fallback():
    # \xe9 is é in latin-1 but invalid UTF-8 on its own.
    raw = _build_metadata_block(b"StreamTitle='Caf\xe9 del Mar';")
    assert decode_metadata_block(raw) == "Café del Mar"


def test_decode_metadata_block_empty_length_byte():
    # Length byte 0 means no metadata in this interval.
    raw = b"\x00"
    assert decode_metadata_block(raw) == ""


def test_iter_titles_skips_audio_and_extracts_titles():
    metaint = 4
    audio_chunk = b"AAAA"
    block_one = _build_metadata_block(b"StreamTitle='Song A';")
    block_two_empty = b"\x00"
    block_three = _build_metadata_block(b"StreamTitle='Song B';")
    payload = audio_chunk + block_one + audio_chunk + block_two_empty + audio_chunk + block_three
    stream = io.BytesIO(payload)

    titles = list(iter_titles(stream, metaint=metaint))

    assert titles == ["Song A", "", "Song B"]


def test_iter_titles_handles_truncated_stream():
    # When the stream ends mid-block, iter_titles just stops cleanly.
    metaint = 4
    payload = b"AAAA" + b"\x02StreamTitle"  # length says 32 bytes, only 11 follow
    stream = io.BytesIO(payload)

    # No exception, no spurious yield.
    assert list(iter_titles(stream, metaint=metaint)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_icy_metadata_reader.py -v`
Expected: All tests fail with `ModuleNotFoundError`.

- [ ] **Step 3: Write the parser**

Create `services/icy_metadata_reader.py`:

```python
"""ICY/Shoutcast in-stream metadata parser.

This module contains only the byte-level parsing logic. The Qt-thread
worker that drives it is added in a separate task and lives in the
same file (we'll grow it in place).

ICY format reminder:
  - Server response includes header `icy-metaint: <N>`.
  - Stream alternates: N audio bytes, 1 length byte, length*16 metadata bytes, N audio bytes, ...
  - Metadata payload is text like:  StreamTitle='Artist - Title';StreamUrl='...';
"""

from __future__ import annotations

import re
from typing import BinaryIO, Iterator

# Match StreamTitle='...' up to the next ';'.
_TITLE_RE = re.compile(r"StreamTitle='([^;]*)';")


def parse_stream_title(metadata_text: str) -> str:
    """Extract the StreamTitle value from a decoded metadata payload."""
    m = _TITLE_RE.search(metadata_text)
    if not m:
        return ""
    return m.group(1).strip()


def decode_metadata_block(block: bytes) -> str:
    """Decode a length-prefixed metadata block to its StreamTitle.

    The block starts with a single byte whose value is the metadata
    length in 16-byte units. Returns "" when the block is empty or the
    block contains no StreamTitle.
    """
    if not block:
        return ""
    length_units = block[0]
    if length_units == 0:
        return ""
    payload = block[1 : 1 + length_units * 16].rstrip(b"\x00")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1", errors="replace")
    return parse_stream_title(text)


def iter_titles(stream: BinaryIO, metaint: int) -> Iterator[str]:
    """Yield StreamTitle strings as they arrive on an ICY-enabled stream.

    The caller is responsible for opening the connection with
    `Icy-MetaData: 1` and reading `icy-metaint` from the headers.

    Yields empty strings for empty metadata blocks (so callers can
    deduplicate using a single 'last seen' variable). Stops iterating
    when the stream is closed or truncated mid-block.
    """
    while True:
        # Discard the audio chunk; we don't decode audio here.
        audio = _read_exact(stream, metaint)
        if audio is None:
            return

        length_byte = stream.read(1)
        if not length_byte:
            return
        length_units = length_byte[0]
        if length_units == 0:
            yield ""
            continue

        meta_bytes = _read_exact(stream, length_units * 16)
        if meta_bytes is None:
            return

        yield decode_metadata_block(length_byte + meta_bytes)


def _read_exact(stream: BinaryIO, n: int) -> bytes | None:
    """Read exactly n bytes, returning None on EOF / truncation."""
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_icy_metadata_reader.py -v`
Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/icy_metadata_reader.py tests/test_icy_metadata_reader.py
git commit -m "Add ICY metadata byte parser (no Qt yet)"
```

---

## Task 4: ICY metadata Qt worker

**Files:**
- Modify: `services/icy_metadata_reader.py` (append `IcyMetadataWorker` class)

This is the Qt wiring around `iter_titles`. It opens the HTTP connection, reads `icy-metaint`, drives the parser, and emits a Qt signal when the title changes. It is meant to live on a `QThread`. Manual integration test is acceptable here — we don't unit-test the network path because `iter_titles` is already covered.

- [ ] **Step 1: Append the worker class to `services/icy_metadata_reader.py`**

Append at the end of the file:

```python
import logging
import urllib.request

from PySide6.QtCore import QObject, Signal, Slot

log = logging.getLogger(__name__)


class IcyMetadataWorker(QObject):
    """Reads ICY metadata from a stream URL on a worker thread.

    Usage:
        thread = QThread()
        worker = IcyMetadataWorker(url)
        worker.moveToThread(thread)
        worker.title_changed.connect(audio_player._on_song_changed)
        thread.started.connect(worker.run)
        thread.start()
        # Later:
        worker.stop()
        thread.quit()
        thread.wait()
    """

    title_changed = Signal(str)
    finished = Signal()

    def __init__(self, url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self._stop_requested = False
        self._response = None

    @Slot()
    def run(self) -> None:
        try:
            req = urllib.request.Request(
                self._url,
                headers={
                    "Icy-MetaData": "1",
                    "User-Agent": "AirStream/1.0",
                },
            )
            self._response = urllib.request.urlopen(req, timeout=10)
            metaint_header = self._response.headers.get("icy-metaint")
            if not metaint_header:
                log.debug("ICY fallback: server did not send icy-metaint, giving up")
                return
            metaint = int(metaint_header)
            last_title = ""
            for title in iter_titles(self._response, metaint=metaint):
                if self._stop_requested:
                    return
                if title != last_title:
                    last_title = title
                    self.title_changed.emit(title)
        except Exception as e:  # pragma: no cover — network paths
            log.debug("ICY fallback worker failed: %s", e)
        finally:
            try:
                if self._response is not None:
                    self._response.close()
            except Exception:
                pass
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self._stop_requested = True
        try:
            if self._response is not None:
                self._response.close()
        except Exception:
            pass
```

- [ ] **Step 2: Verify the existing parser tests still pass**

Run: `pytest tests/test_icy_metadata_reader.py -v`
Expected: All 7 tests still pass (we only appended).

- [ ] **Step 3: Verify the module imports cleanly**

Run: `python -c "from services.icy_metadata_reader import IcyMetadataWorker; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add services/icy_metadata_reader.py
git commit -m "Add Qt worker that drives the ICY parser over HTTP"
```

---

## Task 5: Wire metadata into `AudioPlayer`

**Files:**
- Modify: `services/audio_player.py`
- Create: `tests/test_audio_player_metadata.py`

`AudioPlayer` gains a `song_changed = Signal(str)`, subscribes to `QMediaPlayer.metaDataChanged`, and starts the ICY worker after 8 seconds if no native title arrived. We unit-test the wiring with mocked `QMediaPlayer`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_player_metadata.py`:

```python
"""Unit tests for AudioPlayer metadata wiring.

Strategy: we don't construct a real QMediaPlayer (it requires a
QApplication and GStreamer/DirectShow). Instead we patch the imports
in services.audio_player so AudioPlayer's __init__ uses lightweight
fakes, then drive the slots directly.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_qt(monkeypatch):
    """Replace QMediaPlayer/QAudioOutput with simple Mocks for the duration of a test."""
    # We import inside the fixture so the module-level imports happen with our patches in place.
    fake_player = MagicMock(name="QMediaPlayerInstance")
    fake_audio = MagicMock(name="QAudioOutputInstance")

    fake_module = types.ModuleType("PySide6.QtMultimedia")

    class _FakePlayerClass:
        PlaybackState = MagicMock()
        Error = MagicMock()
        MediaStatus = MagicMock()

        def __new__(cls, *a, **kw):
            return fake_player

    class _FakeAudioOutputClass:
        def __new__(cls, *a, **kw):
            return fake_audio

    class _FakeMediaMetaData:
        Title = "title-key"
        AlbumArtist = "album-artist-key"
        AlbumTitle = "album-title-key"

    fake_module.QMediaPlayer = _FakePlayerClass
    fake_module.QAudioOutput = _FakeAudioOutputClass
    fake_module.QMediaMetaData = _FakeMediaMetaData
    monkeypatch.setitem(sys.modules, "PySide6.QtMultimedia", fake_module)

    # Force re-import so AudioPlayer picks up our fakes.
    if "services.audio_player" in sys.modules:
        del sys.modules["services.audio_player"]

    return fake_player


def _collect(signal):
    """Tiny helper: collect emitted values from a Qt signal."""
    received = []
    signal.connect(lambda v: received.append(v))
    return received


def test_song_changed_emitted_on_native_title(fake_qt, qapp):
    from services.audio_player import AudioPlayer

    fake_qt.metaData.return_value = "Tycho - A Walk"
    player = AudioPlayer()
    received = _collect(player.song_changed)

    player._on_metadata_changed()

    assert received == ["Tycho - A Walk"]


def test_song_changed_dedupes_repeated_titles(fake_qt, qapp):
    from services.audio_player import AudioPlayer

    fake_qt.metaData.return_value = "Tycho - A Walk"
    player = AudioPlayer()
    received = _collect(player.song_changed)

    player._on_metadata_changed()
    player._on_metadata_changed()
    player._on_metadata_changed()

    assert received == ["Tycho - A Walk"]


def test_song_changed_emits_empty_string_on_play(fake_qt, qapp):
    from services.audio_player import AudioPlayer

    player = AudioPlayer()
    received = _collect(player.song_changed)

    player.play("http://example.com/stream")

    # First emit on play() is "" to clear any previous song.
    assert "" in received


def test_song_changed_emits_empty_string_on_stop(fake_qt, qapp):
    from services.audio_player import AudioPlayer

    fake_qt.metaData.return_value = "Tycho - A Walk"
    player = AudioPlayer()
    player._on_metadata_changed()
    received = _collect(player.song_changed)

    player.stop()

    assert received[-1] == ""


def test_blank_native_title_is_ignored(fake_qt, qapp):
    from services.audio_player import AudioPlayer

    fake_qt.metaData.return_value = "   "
    player = AudioPlayer()
    received = _collect(player.song_changed)

    player._on_metadata_changed()

    assert received == []
```

Add a `tests/conftest.py` with the shared `qapp` fixture so we have a Qt application instance for signal handling:

Create `tests/conftest.py`:

```python
import pytest

from PySide6.QtCore import QCoreApplication


@pytest.fixture(scope="session")
def qapp():
    """Provide a QCoreApplication for tests that touch Qt signals."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_audio_player_metadata.py -v`
Expected: All tests fail (most likely on `AttributeError: 'AudioPlayer' object has no attribute 'song_changed'` or similar).

- [ ] **Step 3: Update `services/audio_player.py`**

Replace the file's contents with:

```python
import logging

from PySide6.QtCore import QObject, QTimer, QUrl, QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData

from services.icy_metadata_reader import IcyMetadataWorker

log = logging.getLogger(__name__)

ICY_FALLBACK_DELAY_MS = 8000


class AudioPlayer(QObject):
    state_changed = Signal(str)  # "playing", "paused", "stopped", "error", "buffering"
    song_changed = Signal(str)   # current song title; "" means no song known

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._current_url = ""
        self._last_state = "stopped"
        self._paused = False
        self._last_song = ""

        self._fallback_timer = QTimer(self)
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.setInterval(ICY_FALLBACK_DELAY_MS)
        self._fallback_timer.timeout.connect(self._start_icy_fallback)

        self._icy_thread: QThread | None = None
        self._icy_worker: IcyMetadataWorker | None = None

        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.metaDataChanged.connect(self._on_metadata_changed)

    def play(self, url):
        self._current_url = url
        self._paused = False
        self._stop_icy_fallback()
        self._fallback_timer.stop()
        self._set_song("")
        self._player.stop()
        self._player.setSource(QUrl(url))
        self._player.play()
        self._fallback_timer.start()

    def pause(self):
        # Live streams don't support real pause — stop the stream instead
        self._player.stop()
        self._player.setSource(QUrl())
        self._paused = True
        self._stop_icy_fallback()
        self._fallback_timer.stop()
        self._update_state("paused")

    def resume(self):
        if self._paused and self._current_url:
            self._paused = False
            self._set_song("")
            self._player.setSource(QUrl(self._current_url))
            self._player.play()
            self._fallback_timer.start()

    def stop(self):
        self._paused = False
        self._current_url = ""
        self._stop_icy_fallback()
        self._fallback_timer.stop()
        self._set_song("")
        self._player.stop()
        self._player.setSource(QUrl())
        self._update_state("stopped")

    def toggle_pause(self):
        if self._last_state == "playing" or self._last_state == "buffering":
            self.pause()
        elif self._paused and self._current_url:
            self.resume()

    def is_playing(self):
        return self._last_state == "playing"

    def current_url(self):
        return self._current_url

    def volume(self):
        return round(self._audio_output.volume() * 100)

    def set_volume(self, percent):
        self._audio_output.setVolume(percent / 100.0)

    # ---- metadata ----------------------------------------------------------

    def _on_metadata_changed(self):
        try:
            title = self._player.metaData(QMediaMetaData.Title)
        except Exception:
            return
        if not title:
            return
        title = str(title).strip()
        if not title:
            return
        self._set_song(title)
        # Native worked — cancel any pending fallback.
        self._fallback_timer.stop()
        self._stop_icy_fallback()

    def _set_song(self, song: str):
        if song == self._last_song:
            # Don't dedupe the empty-string clear — callers always want a fresh "" to drop UI state.
            if song != "":
                return
        self._last_song = song
        self.song_changed.emit(song)

    def _start_icy_fallback(self):
        if not self._current_url or self._paused:
            return
        if self._last_song:
            return  # Native already provided a title.
        self._stop_icy_fallback()
        self._icy_thread = QThread()
        self._icy_worker = IcyMetadataWorker(self._current_url)
        self._icy_worker.moveToThread(self._icy_thread)
        self._icy_worker.title_changed.connect(self._on_icy_title)
        self._icy_worker.finished.connect(self._icy_thread.quit)
        self._icy_thread.started.connect(self._icy_worker.run)
        self._icy_thread.start()

    def _on_icy_title(self, title: str):
        title = (title or "").strip()
        if not title:
            return
        self._set_song(title)

    def _stop_icy_fallback(self):
        if self._icy_worker is not None:
            try:
                self._icy_worker.stop()
            except Exception:
                pass
        if self._icy_thread is not None:
            self._icy_thread.quit()
            self._icy_thread.wait(1000)
        self._icy_worker = None
        self._icy_thread = None

    # ---- playback state ----------------------------------------------------

    def _on_playback_state(self, state):
        if self._paused:
            return  # We handle paused state manually
        state_map = {
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
        }
        new_state = state_map.get(state, "stopped")
        self._update_state(new_state)

    def _on_media_status(self, status):
        if self._paused:
            return
        if status == QMediaPlayer.MediaStatus.BufferingMedia:
            self._update_state("buffering")
        elif status == QMediaPlayer.MediaStatus.LoadingMedia:
            self._update_state("buffering")

    def _on_error(self, error, message):
        if error != QMediaPlayer.Error.NoError:
            self._paused = False
            self._stop_icy_fallback()
            self._fallback_timer.stop()
            self._set_song("")
            self._update_state("error")

    def _update_state(self, new_state):
        if new_state != self._last_state:
            self._last_state = new_state
            self.state_changed.emit(new_state)

    def cleanup(self):
        self._stop_icy_fallback()
        self._fallback_timer.stop()
        self._player.stop()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_audio_player_metadata.py -v`
Expected: All 5 tests pass.

- [ ] **Step 5: Run full desktop test suite**

Run: `pytest tests/ -v`
Expected: All 19 tests pass (7 format + 7 ICY parser + 5 audio player).

- [ ] **Step 6: Commit**

```bash
git add services/audio_player.py tests/test_audio_player_metadata.py tests/conftest.py
git commit -m "Wire native + ICY-fallback metadata into AudioPlayer"
```

---

## Task 6: Update `PlayerControls` to consume `song_changed`

**Files:**
- Modify: `app/player_controls.py`

`PlayerControls` adds `_current_song` and a `_refresh_labels()` method that delegates string formatting to `services.now_playing_format`. The three existing setter spots all funnel through `_refresh_labels()`. We do **not** call `announce()` from `_on_song_changed` (silent in-app, per the spec).

- [ ] **Step 1: Replace the contents of `app/player_controls.py`**

```python
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QLabel

from app.accessibility import set_accessible_props, announce
from services.now_playing_format import button_strings, label_string


class PlayerControls(QObject):
    def __init__(self, player, parent_layout, parent=None):
        super().__init__(parent)
        self._player = player
        self._current_station = None
        self._current_song = ""
        self._last_state = "stopped"
        self._announced_loading = False

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.fav_button = QPushButton("Favorite")
        set_accessible_props(self.fav_button, "Add to favorites")

        self.play_button = QPushButton("Play")
        set_accessible_props(self.play_button, "Play")

        self.now_playing_label = QLabel("Not playing")
        set_accessible_props(self.now_playing_label, "Not playing")

        layout.addWidget(self.fav_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.now_playing_label, 1)

        parent_layout.addLayout(layout)

        self.play_button.clicked.connect(self._on_play_clicked)
        self._player.state_changed.connect(self._on_state_changed)
        self._player.song_changed.connect(self._on_song_changed)

    def set_station(self, station):
        self._current_station = station
        self._refresh_labels()

    def current_station(self):
        return self._current_station

    def play_station(self, station):
        self._current_station = station
        self._current_song = ""
        self._announced_loading = False
        url = station.get("url_resolved") or station.get("url", "")
        if url:
            self._player.play(url)
            self._refresh_labels()
            announce(self.now_playing_label, label_string(
                state="buffering", station=station, song=""
            ))

    def toggle_pause(self):
        if self._current_station:
            self._player.toggle_pause()

    def update_favorite_button(self, is_fav):
        if is_fav:
            self.fav_button.setText("Unfavorite")
            set_accessible_props(self.fav_button, "Remove from favorites")
        else:
            self.fav_button.setText("Favorite")
            set_accessible_props(self.fav_button, "Add to favorites")

    def _on_play_clicked(self):
        if not self._current_station:
            return
        self.toggle_pause()

    def _on_state_changed(self, state):
        self._last_state = state

        if state == "playing":
            self._announced_loading = False
        elif state == "paused":
            announce(self.play_button, "Paused")
        elif state == "error":
            announce(self.now_playing_label, "Could not connect to this station")
        elif state == "buffering":
            if not self._announced_loading:
                self._announced_loading = True
                announce(self.play_button, "Loading")

        self._refresh_labels()

    def _on_song_changed(self, song):
        self._current_song = song or ""
        self._refresh_labels()
        # Note: deliberately no announce() here — silent in-app per design.

    def _refresh_labels(self):
        btn_text, btn_a11y = button_strings(
            state=self._last_state,
            station=self._current_station,
            song=self._current_song,
        )
        self.play_button.setText(btn_text)
        set_accessible_props(self.play_button, btn_a11y)

        lbl = label_string(
            state=self._last_state,
            station=self._current_station,
            song=self._current_song,
        )
        self.now_playing_label.setText(lbl)
        set_accessible_props(self.now_playing_label, lbl)
```

- [ ] **Step 2: Run desktop tests to confirm nothing regressed**

Run: `pytest tests/ -v`
Expected: All 19 tests still pass.

- [ ] **Step 3: Smoke-launch the desktop app**

Run: `python main.py`
Expected:
- Window opens.
- Picking a station starts playback. Tabbing to the play button reads `Pause, now playing <station>` (or `Pause, now playing <song> on <station>` once metadata arrives — most common stations should produce a song within 10 seconds).
- Pressing Space pauses; tabbing to the play button reads `Play, <station> paused`.
- Pressing Escape reads `Not playing`.

If anything misbehaves, fix before committing.

- [ ] **Step 4: Commit**

```bash
git add app/player_controls.py
git commit -m "Wire now-playing song into desktop play button + label"
```

---

## Task 7: Drop redundant manual reset in `MainWindow._on_stop`

**Files:**
- Modify: `app/main_window.py:409-413`

`AudioPlayer.stop()` now emits `song_changed("")` and `state_changed("stopped")`, which together drive `_refresh_labels()` to render `"Not playing"`. The manual setText/announce in `_on_stop` is now redundant.

- [ ] **Step 1: Locate the `_on_stop` method**

Read `app/main_window.py:409-413`:

```python
    def _on_stop(self):
        self._player.stop()
        self.player_controls.now_playing_label.setText("Not playing")
        set_accessible_props(self.player_controls.now_playing_label, "Not playing")
        announce(self, "Playback stopped")
```

- [ ] **Step 2: Replace it with a minimal version**

```python
    def _on_stop(self):
        self._player.stop()
        announce(self, "Playback stopped")
```

(Use Edit to replace exactly those four lines: keep `self._player.stop()` and the `announce` line, drop the two `setText`/`set_accessible_props` lines.)

- [ ] **Step 3: Smoke-launch and verify Escape still resets the label**

Run: `python main.py`
Pick a station, play, then press Escape.
Expected: button reads `Play`, label reads `Not playing`, screen reader says `Playback stopped`.

- [ ] **Step 4: Run desktop tests**

Run: `pytest tests/ -v`
Expected: All 19 tests still pass.

- [ ] **Step 5: Commit**

```bash
git add app/main_window.py
git commit -m "Drop redundant label reset in _on_stop (driven by player events now)"
```

---

## Task 8: Add `currentSongStream` to mobile `AudioPlayerHandler`

**Files:**
- Modify: `mobile/lib/services/audio_service.dart`
- Create: `mobile/test/audio_service_test.dart`

`AudioPlayerHandler` exposes `Stream<String> get currentSongStream` and updates `mediaItem` when ICY metadata arrives.

- [ ] **Step 1: Write the failing test**

Create `mobile/test/audio_service_test.dart`:

```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:audio_service/audio_service.dart';
import 'package:airstream/services/audio_service.dart';
import 'package:airstream/models/station.dart';

class _Recorder<T> {
  final List<T> events = [];
  late final StreamSubscription<T> sub;
  _Recorder(Stream<T> s) {
    sub = s.listen(events.add);
  }
  void cancel() => sub.cancel();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('currentSongStream emits empty string initially after playStation', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );

    final rec = _Recorder<String>(handler.currentSongStream);
    // Note: we can't await playStation() (it tries real network) — instead we
    // call the helper that resets song state directly.
    handler.debugResetSongFor(station);

    await Future<void>.delayed(const Duration(milliseconds: 10));
    expect(rec.events, contains(''));
    rec.cancel();
  });

  test('handleIcyTitle updates currentSongStream and mediaItem', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final rec = _Recorder<String>(handler.currentSongStream);
    final mediaRec = _Recorder<MediaItem?>(handler.mediaItem);

    handler.debugHandleIcyTitle('Tycho - A Walk');
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(rec.events.last, 'Tycho - A Walk');
    expect(mediaRec.events.last?.title, 'Tycho - A Walk');
    expect(mediaRec.events.last?.artist, 'Soma FM');

    rec.cancel();
    mediaRec.cancel();
  });

  test('handleIcyTitle dedupes identical titles', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final rec = _Recorder<String>(handler.currentSongStream);
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('Tycho - A Walk');

    await Future<void>.delayed(const Duration(milliseconds: 10));

    final tychoCount = rec.events.where((e) => e == 'Tycho - A Walk').length;
    expect(tychoCount, 1);
    rec.cancel();
  });

  test('handleIcyTitle empty title falls back to station as MediaItem title', () async {
    final handler = AudioPlayerHandler();
    final station = Station(
      stationuuid: 'uuid-1',
      name: 'Soma FM',
      urlResolved: 'http://example.com/stream',
      country: 'USA',
    );
    handler.debugResetSongFor(station);

    final mediaRec = _Recorder<MediaItem?>(handler.mediaItem);
    handler.debugHandleIcyTitle('Tycho - A Walk');
    handler.debugHandleIcyTitle('');

    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(mediaRec.events.last?.title, 'Soma FM');
    expect(mediaRec.events.last?.artist, 'USA');
    mediaRec.cancel();
  });
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mobile && flutter test test/audio_service_test.dart`
Expected: All four tests fail (compile error: `currentSongStream`, `debugResetSongFor`, `debugHandleIcyTitle` don't exist).

- [ ] **Step 3: Update `mobile/lib/services/audio_service.dart`**

Replace the file contents with:

```dart
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:audio_service/audio_service.dart';
import '../models/station.dart';

class AudioPlayerHandler extends BaseAudioHandler {
  final _player = AudioPlayer();
  final _songController = StreamController<String>.broadcast();

  String _currentUrl = '';
  bool _isPaused = false;
  Station? currentStation;
  String _currentSong = '';

  AudioPlayerHandler() {
    // Forward just_audio state to audio_service's playbackState.
    _player.playerStateStream.listen((state) {
      if (_isPaused) return;
      final playing = state.playing;
      final processingState = switch (state.processingState) {
        ProcessingState.idle => AudioProcessingState.idle,
        ProcessingState.loading => AudioProcessingState.loading,
        ProcessingState.buffering => AudioProcessingState.buffering,
        ProcessingState.ready => AudioProcessingState.ready,
        ProcessingState.completed => AudioProcessingState.completed,
      };
      playbackState.add(playbackState.value.copyWith(
        controls: [
          if (playing) MediaControl.pause else MediaControl.play,
          MediaControl.stop,
        ],
        systemActions: const {MediaAction.play, MediaAction.pause, MediaAction.stop},
        playing: playing,
        processingState: processingState,
      ));
    });

    // ICY metadata for live streams: extract StreamTitle and surface it.
    _player.icyMetadataStream.listen((event) {
      final title = event?.info?.title?.trim() ?? '';
      _handleIcyTitle(title);
    });
  }

  Stream<PlayerState> get playerStateStream => _player.playerStateStream;

  /// Stream of the current song title. Emits '' when no song is known.
  Stream<String> get currentSongStream => _songController.stream;

  String get currentSong => _currentSong;

  Future<void> playStation(Station station) async {
    _currentUrl = station.urlResolved;
    currentStation = station;
    _isPaused = false;
    _resetSongFor(station);

    try {
      await _player.setAudioSource(
        AudioSource.uri(Uri.parse(station.urlResolved)),
      );
      await _player.play();
    } catch (e) {
      debugPrint('AIRSTREAM: retrying with headers: $e');
      await _player.setAudioSource(
        AudioSource.uri(
          Uri.parse(station.urlResolved),
          headers: {'User-Agent': 'AirStream/1.0'},
        ),
      );
      await _player.play();
    }
  }

  @override
  Future<void> play() async {
    if (_isPaused && _currentUrl.isNotEmpty) {
      _isPaused = false;
      await _player.setUrl(_currentUrl);
      await _player.play();
    }
  }

  @override
  Future<void> pause() async {
    _isPaused = true;
    await _player.stop();
    playbackState.add(playbackState.value.copyWith(
      controls: [MediaControl.play, MediaControl.stop],
      systemActions: const {MediaAction.play, MediaAction.pause, MediaAction.stop},
      playing: false,
      processingState: AudioProcessingState.ready,
    ));
  }

  @override
  Future<void> stop() async {
    _isPaused = false;
    _currentUrl = '';
    final hadStation = currentStation != null;
    currentStation = null;
    if (hadStation) {
      _currentSong = '';
      _songController.add('');
    }
    await _player.stop();
    playbackState.add(playbackState.value.copyWith(
      controls: [],
      playing: false,
      processingState: AudioProcessingState.idle,
    ));
    await super.stop();
  }

  bool get isPaused => _isPaused;
  bool get isPlaying => _player.playing && !_isPaused;
  String get currentUrl => _currentUrl;

  void _resetSongFor(Station station) {
    _currentSong = '';
    _songController.add('');
    mediaItem.add(MediaItem(
      id: station.urlResolved,
      title: station.name,
      artist: station.country,
    ));
  }

  void _handleIcyTitle(String title) {
    if (title == _currentSong) return;
    _currentSong = title;
    _songController.add(title);
    final station = currentStation;
    if (station == null) return;
    if (title.isNotEmpty) {
      mediaItem.add(MediaItem(
        id: station.urlResolved,
        title: title,
        artist: station.name,
      ));
    } else {
      mediaItem.add(MediaItem(
        id: station.urlResolved,
        title: station.name,
        artist: station.country,
      ));
    }
  }

  // ---- test hooks --------------------------------------------------------
  // These let widget/unit tests drive song state without going through the
  // network. They are deliberately named with the `debug` prefix to discourage
  // production callers.

  @visibleForTesting
  void debugResetSongFor(Station station) {
    currentStation = station;
    _resetSongFor(station);
  }

  @visibleForTesting
  void debugHandleIcyTitle(String title) {
    _handleIcyTitle(title);
  }

  // ---- lifecycle ---------------------------------------------------------

  void dispose() {
    _songController.close();
    _player.dispose();
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd mobile && flutter test test/audio_service_test.dart`
Expected: All four tests pass.

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/services/audio_service.dart mobile/test/audio_service_test.dart
git commit -m "Wire ICY metadata into mobile AudioPlayerHandler"
```

---

## Task 9: Two-line now-playing bar on mobile

**Files:**
- Modify: `mobile/lib/screens/home_screen.dart:413-460` (the `if (_currentStation != null)` block)

The bar wraps a nested `StreamBuilder<String>` over `audioHandler.currentSongStream` to render two lines when a song is known, and one line when it isn't.

- [ ] **Step 1: Replace the existing bar block**

Find the `// Player bar` block in `mobile/lib/screens/home_screen.dart` (starts at line 413 with `if (_currentStation != null)`) and replace through the closing `),` of the outer `StreamBuilder` (line 460).

New block:

```dart
          // Player bar
          if (_currentStation != null)
            StreamBuilder<PlayerState>(
              stream: widget.audioHandler.playerStateStream,
              builder: (ctx, snapshot) {
                final state = snapshot.data;
                final isActive = widget.audioHandler.isPlaying;
                final isPaused = widget.audioHandler.isPaused;
                final buffering = state?.processingState == ProcessingState.loading ||
                    state?.processingState == ProcessingState.buffering;
                final showPause = isActive && !isPaused;
                return StreamBuilder<String>(
                  stream: widget.audioHandler.currentSongStream,
                  initialData: widget.audioHandler.currentSong,
                  builder: (ctx, songSnap) {
                    final song = (songSnap.data ?? '').trim();
                    final stationName = _currentStation!.name;
                    final semanticsLabel = song.isEmpty
                        ? 'Now playing: $stationName'
                        : 'Now playing: $song on $stationName';
                    return Container(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: SafeArea(
                        top: false,
                        child: Row(
                          children: [
                            Expanded(
                              child: Semantics(
                                label: semanticsLabel,
                                container: true,
                                excludeSemantics: true,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (song.isNotEmpty)
                                      Text(
                                        song,
                                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                              fontWeight: FontWeight.w600,
                                            ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    Text(
                                      stationName,
                                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurfaceVariant,
                                          ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            if (buffering && !isPaused)
                              const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            else
                              IconButton(
                                icon: Icon(
                                  showPause ? Icons.pause_circle_filled : Icons.play_circle_filled,
                                  semanticLabel: showPause ? 'Pause' : 'Play',
                                ),
                                iconSize: 40,
                                onPressed: _togglePause,
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
```

- [ ] **Step 2: Run the existing audio_service test to confirm no regression**

Run: `cd mobile && flutter test test/audio_service_test.dart`
Expected: 4 tests pass.

- [ ] **Step 3: Smoke-launch on Android (or emulator)**

Run: `cd mobile && flutter run`
Expected:
- Pick a station that's known to broadcast metadata (e.g., a SomaFM channel).
- The bar starts as a single line (station name).
- Within ~10 seconds, the song title appears as a bold line above the station name.
- Pulling down the notification shade shows the song as the title and the station as the artist.
- Pause: bar stays visible; song line keeps the last seen title until the next station change.
- Pick a different station: bar resets to single line until the next song arrives.

- [ ] **Step 4: Commit**

```bash
git add mobile/lib/screens/home_screen.dart
git commit -m "Show song + station as two lines in mobile now-playing bar"
```

---

## Task 10: Manual end-to-end smoke

This step has no code changes — it's a final cross-check before merging.

- [ ] **Step 1: Desktop smoke**

Run: `python main.py`
- Pick a station. Tab to the play button. Verify the screen reader announces `Pause, now playing <station>` immediately and `Pause, now playing <song> on <station>` once metadata arrives.
- Verify the visible label below the button mirrors the same info (`Now playing: <song> — <station>`).
- Press Space to pause. Tab to the play button. Verify it reads `Play, <station> paused` and the label says `<station> — paused`.
- Press Escape. Verify both reset to `Play` / `Not playing`.
- Pick a station that doesn't broadcast metadata (e.g., a low-traffic station from the default list — try a few). Verify the fallback after ~8 seconds either picks up the title via the ICY worker, or stays gracefully on `Pause, now playing <station>`.

- [ ] **Step 2: Mobile smoke**

Run: `cd mobile && flutter run` on a real Android device or emulator.
- Pick a station. Verify the bar shows the station name on its own. Within ~10 seconds, verify the song appears as a bold top line.
- Lock the screen. Verify the lockscreen / notification shade shows the song as the title and the station as the artist.
- Connect a Bluetooth speaker / headphones. Verify the song appears on its display where applicable.
- Pause from the system notification. Verify pause works.
- Pick a different station from the app. Verify the bar resets and the new station's song eventually appears.

- [ ] **Step 3: Final commit (only if you fixed anything during smoke)**

If the smoke passed cleanly, no commit. Otherwise commit fixes with descriptive messages and re-run the smoke.

---

## Self-review notes

- **Spec coverage:** every row of the format table → Task 2; native desktop metadata → Task 5; ICY parser → Tasks 3-4; ICY fallback wiring → Task 5; PlayerControls integration → Task 6; redundant reset removal → Task 7; mobile native ICY + MediaItem update → Task 8; mobile bar → Task 9; non-goals (album art, history, audio fingerprinting) are honored — none of the tasks add them.
- **Type/method consistency:** `song_changed` (Signal[str]) used identically across audio_player.py and player_controls.py; `currentSongStream` / `_currentSong` / `_handleIcyTitle` consistent across audio_service.dart and tests; `button_strings`/`label_string` signatures match between format module and player_controls; `iter_titles` / `decode_metadata_block` / `parse_stream_title` consistent between parser and tests.
- **No placeholders:** every step has explicit code or commands.
