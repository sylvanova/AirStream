from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from app.accessibility import set_accessible_props, announce


class PlayerControls(QWidget):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self._player = player
        self._current_station = None
        self._announced_loading = False

        layout = QHBoxLayout(self)
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

        self.play_button.clicked.connect(self._on_play_clicked)
        self._player.state_changed.connect(self._on_state_changed)

    def set_station(self, station):
        self._current_station = station

    def current_station(self):
        return self._current_station

    def play_station(self, station):
        self._current_station = station
        self._announced_loading = False
        url = station.get("url_resolved") or station.get("url", "")
        if url:
            self._player.play(url)
            name = station.get("name", "Unknown")
            self.now_playing_label.setText(f"Now playing: {name}")
            set_accessible_props(self.now_playing_label, f"Now playing: {name}")
            announce(self, f"Now playing: {name}")

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
        if state == "playing":
            self._announced_loading = False
            self.play_button.setText("Pause")
            set_accessible_props(self.play_button, "Pause")
        elif state == "paused":
            self.play_button.setText("Play")
            set_accessible_props(self.play_button, "Play")
            announce(self, "Paused")
        elif state == "error":
            self.play_button.setText("Play")
            set_accessible_props(self.play_button, "Play")
            self.now_playing_label.setText("Playback error")
            set_accessible_props(self.now_playing_label, "Playback error")
            announce(self, "Could not connect to this station")
        elif state == "stopped":
            self.play_button.setText("Play")
            set_accessible_props(self.play_button, "Play")
        elif state == "buffering":
            if not self._announced_loading:
                self._announced_loading = True
                announce(self, "Loading")
