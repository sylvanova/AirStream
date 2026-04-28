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
