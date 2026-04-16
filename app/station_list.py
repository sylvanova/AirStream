from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QScrollArea, QPushButton, QWidget,
    QSizePolicy, QApplication,
)

from app.accessibility import set_accessible_props


class StationButton(QPushButton):
    """A single station row styled as a flat button for accessibility."""

    def __init__(self, station, parent=None):
        self.station = station
        name = station.get("name", "Unknown")
        country = station.get("country", "")
        tags = station.get("tags", "")
        bitrate = station.get("bitrate", 0)

        parts = [name]
        if country:
            parts.append(country)
        if tags:
            parts.append(tags)
        if bitrate:
            parts.append(f"{bitrate} kbps")

        display = "  \u2014  ".join(parts)
        accessible = ", ".join(parts)

        super().__init__(display, parent)
        set_accessible_props(self, accessible)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # NoFocus: Tab skips individual buttons. Focus is managed by the parent list.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(
            "QPushButton { text-align: left; padding: 6px 8px; border: none; }"
            "QPushButton:focus { background: palette(highlight); color: palette(highlighted-text); }"
        )


class StationListView(QGroupBox):
    station_activated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("Stations", parent)
        set_accessible_props(self, "Stations")
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

        self._buttons = []
        self._stations = []
        self._current_index = -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        outer.addWidget(self._scroll)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)
        self._layout.addStretch()
        self._scroll.setWidget(self._container)

    def set_stations(self, stations):
        for btn in self._buttons:
            self._layout.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()
        self._stations = stations
        self._current_index = -1

        for i, station in enumerate(stations):
            btn = StationButton(station)
            btn.clicked.connect(lambda checked, s=station: self._activate(s))
            self._layout.insertWidget(i, btn)
            self._buttons.append(btn)

        if stations:
            self._current_index = 0
            self._focus_current()

    def selected_station(self):
        if 0 <= self._current_index < len(self._stations):
            return self._stations[self._current_index]
        return None

    def station_count(self):
        return len(self._stations)

    def _activate(self, station):
        for i, s in enumerate(self._stations):
            if s is station:
                self._current_index = i
                break
        self.station_activated.emit(station)

    def _focus_current(self):
        if self._buttons and 0 <= self._current_index < len(self._buttons):
            btn = self._buttons[self._current_index]
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setFocus()
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._scroll.ensureWidgetVisible(btn)

    def focusInEvent(self, event):
        # When Tab lands on the station list, focus the current station button
        if self._buttons:
            if self._current_index < 0:
                self._current_index = 0
            self._focus_current()
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            if not self._buttons:
                return
            if key == Qt.Key.Key_Down:
                new = min(self._current_index + 1, len(self._buttons) - 1)
            else:
                new = max(self._current_index - 1, 0)
            if new != self._current_index:
                self._current_index = new
                self._focus_current()
            return

        if key == Qt.Key.Key_Tab:
            # Tab exits the station list — move to the next widget in tab order
            self.focusNextChild()
            return

        if key == (Qt.Key.Key_Tab | Qt.Key.Key_Shift):
            self.focusPreviousChild()
            return

        super().keyPressEvent(event)
