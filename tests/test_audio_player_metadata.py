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
