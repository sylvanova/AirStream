import vlc  # noqa: F401 — imported at module level after VLC check in main.py
from PySide6.QtCore import QObject, QTimer, Signal


class AudioPlayer(QObject):
    state_changed = Signal(str)  # "playing", "paused", "stopped", "error", "buffering"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._instance = vlc.Instance("--no-video", "--quiet")
        self._player = self._instance.media_player_new()
        self._current_url = ""
        self._last_state = "stopped"

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()

    def play(self, url):
        self._current_url = url
        media = self._instance.media_new(url)
        self._player.set_media(media)
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()
        self._update_state("stopped")

    def toggle_pause(self):
        if self._last_state == "playing":
            self.pause()
        elif self._last_state == "paused":
            self.pause()  # VLC pause toggles
        elif self._current_url:
            self.play(self._current_url)

    def is_playing(self):
        return self._last_state == "playing"

    def current_url(self):
        return self._current_url

    def _poll_state(self):
        state = self._player.get_state()
        state_map = {
            vlc.State.Playing: "playing",
            vlc.State.Paused: "paused",
            vlc.State.Stopped: "stopped",
            vlc.State.Ended: "stopped",
            vlc.State.Error: "error",
            vlc.State.Opening: "buffering",
            vlc.State.Buffering: "buffering",
            vlc.State.NothingSpecial: "stopped",
        }
        new_state = state_map.get(state, "stopped")
        self._update_state(new_state)

    def _update_state(self, new_state):
        if new_state != self._last_state:
            self._last_state = new_state
            self.state_changed.emit(new_state)

    def cleanup(self):
        self._poll_timer.stop()
        self._player.stop()
        self._player.release()
        self._instance.release()
