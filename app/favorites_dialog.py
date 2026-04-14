from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

from app.accessibility import set_accessible_props, announce


class AddStationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Custom Station")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Station Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Radio Station")
        set_accessible_props(self.name_edit, "Station name")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Stream URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://stream.example.com/radio.mp3")
        set_accessible_props(self.url_edit, "Stream URL")
        layout.addWidget(self.url_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.name_edit.setFocus()

    def _validate_and_accept(self):
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a station name.")
            self.name_edit.setFocus()
            return
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a stream URL.")
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

        layout = QVBoxLayout(self)

        all_stations = favorite_stations + custom_stations

        self.station_list = QListWidget()
        set_accessible_props(self.station_list, "Favorites")
        layout.addWidget(self.station_list)

        if not all_stations:
            item = QListWidgetItem("No favorites yet")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.station_list.addItem(item)
        else:
            for s in all_stations:
                name = s.get("name", "Unknown")
                country = s.get("country", "")
                label = f"{name}, {country}" if country else name
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, s)
                self.station_list.addItem(item)
            self.station_list.setCurrentRow(0)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        set_accessible_props(self.play_btn, "Play")
        self.play_btn.clicked.connect(self._on_play)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.play_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.station_list.itemActivated.connect(self._on_item_activated)
        self.station_list.setFocus()

        # Announce just the count and first station name
        if all_stations:
            first = all_stations[0].get("name", "Unknown")
            QTimer.singleShot(200, lambda: announce(self, f"Favorites. {first}"))
        else:
            QTimer.singleShot(200, lambda: announce(self, "No favorites"))

    def _on_play(self):
        item = self.station_list.currentItem()
        if item:
            station = item.data(Qt.ItemDataRole.UserRole)
            if station:
                self._selected_station = station
                self.accept()

    def _on_item_activated(self, item):
        station = item.data(Qt.ItemDataRole.UserRole)
        if station:
            self._selected_station = station
            self.accept()

    def selected_station(self):
        return self._selected_station
