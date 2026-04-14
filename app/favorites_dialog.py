from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
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


class FavoritesDialog(QDialog):
    def __init__(self, favorite_stations, custom_stations, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Favorites")
        self.setMinimumSize(500, 400)
        self._selected_station = None
        self._all_stations = favorite_stations + custom_stations

        layout = QVBoxLayout(self)

        self.station_list = QListWidget()
        set_accessible_props(self.station_list, "Favorites")
        layout.addWidget(self.station_list)

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

        self.station_list.itemActivated.connect(self._on_item_activated)
        self.station_list.setFocus()

        if self._all_stations:
            first = self._all_stations[0].get("name", "Unknown")
            QTimer.singleShot(200, lambda: announce(self, f"Favorites. {first}"))
        else:
            QTimer.singleShot(200, lambda: announce(self, "No favorites"))

    def _populate_list(self):
        self.station_list.clear()
        if not self._all_stations:
            item = QListWidgetItem("No favorites yet")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.station_list.addItem(item)
        else:
            for s in self._all_stations:
                name = s.get("name", "Unknown")
                country = s.get("country", "")
                label = f"{name}, {country}" if country else name
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, s)
                self.station_list.addItem(item)
            self.station_list.setCurrentRow(0)

    def _on_play(self):
        item = self.station_list.currentItem()
        if item:
            station = item.data(Qt.ItemDataRole.UserRole)
            if station:
                self._selected_station = station
                self.accept()

    def _on_remove(self):
        item = self.station_list.currentItem()
        if not item:
            return
        station = item.data(Qt.ItemDataRole.UserRole)
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

    def _on_item_activated(self, item):
        station = item.data(Qt.ItemDataRole.UserRole)
        if station:
            self._selected_station = station
            self.accept()

    def selected_station(self):
        return self._selected_station
