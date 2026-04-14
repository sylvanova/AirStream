from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import QTableView, QAbstractItemView, QHeaderView

from app.accessibility import set_accessible_props


COLUMNS = ["Name", "Country", "Tags", "Bitrate"]


class StationTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stations = []

    def set_stations(self, stations):
        self.beginResetModel()
        self._stations = stations
        self.endResetModel()

    def station_at(self, row):
        if 0 <= row < len(self._stations):
            return self._stations[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._stations)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        station = self._stations[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return station.get("name", "Unknown")
            elif col == 1:
                return station.get("country", "")
            elif col == 2:
                return station.get("tags", "")
            elif col == 3:
                bitrate = station.get("bitrate", 0)
                return f"{bitrate} kbps" if bitrate else ""

        if role == Qt.ItemDataRole.AccessibleTextRole:
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
            return ", ".join(parts)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None


class StationListView(QTableView):
    station_activated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = StationTableModel(self)
        self.setModel(self._model)

        set_accessible_props(
            self,
            "Station list",
            "List of radio stations. Use arrow keys to navigate, Enter to play.",
        )

        # Selection behavior
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)

        # Column sizing
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Activate on Enter/double-click
        self.activated.connect(self._on_activated)

    def set_stations(self, stations):
        self._model.set_stations(stations)
        if stations:
            self.selectRow(0)

    def selected_station(self):
        indexes = self.selectionModel().selectedRows()
        if indexes:
            return self._model.station_at(indexes[0].row())
        return None

    def station_count(self):
        return self._model.rowCount()

    def _on_activated(self, index):
        station = self._model.station_at(index.row())
        if station:
            self.station_activated.emit(station)
