from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QWidget,
    QLabel,
    QSizePolicy,
    QApplication,
)

from app.accessibility import set_accessible_props, announce
from services import storage


class AddStationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Station")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Station name")
        set_accessible_props(self.name_edit, "Station name")
        layout.addWidget(self.name_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Stream URL")
        set_accessible_props(self.url_edit, "Stream URL")
        layout.addWidget(self.url_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Add")
        set_accessible_props(self.ok_btn, "Add")
        self.ok_btn.clicked.connect(self._validate_and_accept)

        self.cancel_btn = QPushButton("Cancel")
        set_accessible_props(self.cancel_btn, "Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.name_edit.setFocus()
        QTimer.singleShot(200, lambda: announce(self, "Add station"))

    def _validate_and_accept(self):
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        if not name:
            announce(self, "Enter a station name")
            self.name_edit.setFocus()
            return
        if not url:
            announce(self, "Enter a stream URL")
            self.url_edit.setFocus()
            return
        self.accept()

    def station_name(self):
        return self.name_edit.text().strip()

    def station_url(self):
        return self.url_edit.text().strip()


class _FavButton(QPushButton):
    """A favorite station button with NoFocus policy for managed navigation."""
    pass


class FavoritesDialog(QDialog):
    def __init__(self, favorite_stations, custom_stations, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Favorites")
        self.setMinimumSize(500, 400)
        self._selected_station = None
        self._all_stations = favorite_stations + custom_stations
        self._buttons = []
        self._current_index = 0

        layout = QVBoxLayout(self)

        # Station list as a group box with buttons
        self._group = QGroupBox("Favorites")
        set_accessible_props(self._group, "Favorites")
        self._group.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        group_layout = QVBoxLayout(self._group)
        group_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        group_layout.addWidget(self._scroll)

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(1)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._container)

        layout.addWidget(self._group, 1)

        self._populate_list()

        btn_layout = QHBoxLayout()

        self.play_btn = QPushButton("Play")
        set_accessible_props(self.play_btn, "Play")
        self.play_btn.clicked.connect(self._on_play)

        self.remove_btn = QPushButton("Remove")
        set_accessible_props(self.remove_btn, "Remove from favorites")
        self.remove_btn.clicked.connect(self._on_remove)

        self.close_btn = QPushButton("Close")
        set_accessible_props(self.close_btn, "Close")
        self.close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        # Install event filter for keyboard navigation
        QApplication.instance().installEventFilter(self)

        if self._all_stations and self._buttons:
            self._focus_current()
            first = self._all_stations[0].get("name", "Unknown")
            QTimer.singleShot(200, lambda: announce(self, f"Favorites. {first}"))
        else:
            self.close_btn.setFocus()
            QTimer.singleShot(200, lambda: announce(self, "No favorites"))

    def _populate_list(self):
        for btn in self._buttons:
            self._list_layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        if not self._all_stations:
            label = QLabel("No favorites yet")
            set_accessible_props(label, "No favorites yet")
            self._list_layout.insertWidget(0, label)
            return

        for i, station in enumerate(self._all_stations):
            name = station.get("name", "Unknown")
            country = station.get("country", "")
            label = f"{name}, {country}" if country else name

            btn = _FavButton(label)
            set_accessible_props(btn, label)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 6px 8px; border: none; }"
                "QPushButton:focus { background: palette(highlight); color: palette(highlighted-text); }"
            )
            btn.setProperty("station", station)
            btn.clicked.connect(lambda checked, s=station: self._on_item_activated(s))
            self._list_layout.insertWidget(i, btn)
            self._buttons.append(btn)

        self._current_index = 0

    def _focus_current(self):
        if self._buttons and 0 <= self._current_index < len(self._buttons):
            btn = self._buttons[self._current_index]
            btn.setFocus()
            self._scroll.ensureWidgetVisible(btn)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            focused = QApplication.focusWidget()
            key = event.key()
            modifiers = event.modifiers()

            if isinstance(focused, _FavButton):
                # Arrow keys navigate within favorites
                if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                    if key == Qt.Key.Key_Down:
                        new_idx = min(self._current_index + 1, len(self._buttons) - 1)
                    else:
                        new_idx = max(self._current_index - 1, 0)
                    if new_idx != self._current_index:
                        self._current_index = new_idx
                        self._focus_current()
                    return True

                # Tab exits the favorites list to the action buttons
                if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                    self.play_btn.setFocus()
                    return True
                if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and modifiers == Qt.KeyboardModifier.ShiftModifier:
                    self.close_btn.setFocus()
                    return True
                if key == Qt.Key.Key_Backtab:
                    self.close_btn.setFocus()
                    return True

                # Enter activates the focused favorite
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    focused.click()
                    return True

        return super().eventFilter(obj, event)

    def _focused_station(self):
        if 0 <= self._current_index < len(self._all_stations):
            return self._all_stations[self._current_index]
        return None

    def _on_play(self):
        station = self._focused_station()
        if station:
            self._selected_station = station
            self.accept()

    def _on_remove(self):
        station = self._focused_station()
        if not station:
            return

        name = station.get("name", "Unknown")
        uuid = station.get("stationuuid", "")

        if station.get("is_custom"):
            storage.remove_custom_station(uuid)
        else:
            storage.remove_favorite(uuid)

        self._all_stations = [s for s in self._all_stations if s.get("stationuuid") != uuid]
        self._populate_list()
        announce(self, f"{name} removed")

        if not self._all_stations:
            announce(self, "No favorites")
        elif self._buttons:
            self._current_index = min(self._current_index, len(self._buttons) - 1)
            self._focus_current()

    def _on_item_activated(self, station):
        self._selected_station = station
        self.accept()

    def selected_station(self):
        return self._selected_station
