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
