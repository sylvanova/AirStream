from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioPlayer(QObject):
    state_changed = Signal(str)  # "playing", "paused", "stopped", "error", "buffering"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._current_url = ""
        self._last_state = "stopped"
        self._paused = False

        self._player.playbackStateChanged.connect(self._on_playback_state)
        self._player.errorOccurred.connect(self._on_error)
        self._player.mediaStatusChanged.connect(self._on_media_status)

    def play(self, url):
        self._current_url = url
        self._paused = False
        self._player.stop()
        self._player.setSource(QUrl(url))
        self._player.play()

    def pause(self):
        # Live streams don't support real pause — stop the stream instead
        self._player.stop()
        self._player.setSource(QUrl())
        self._paused = True
        self._update_state("paused")

    def resume(self):
        if self._paused and self._current_url:
            self._paused = False
            self._player.setSource(QUrl(self._current_url))
            self._player.play()

    def stop(self):
        self._paused = False
        self._current_url = ""
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
            self._update_state("error")

    def _update_state(self, new_state):
        if new_state != self._last_state:
            self._last_state = new_state
            self.state_changed.emit(new_state)

    def cleanup(self):
        self._player.stop()
