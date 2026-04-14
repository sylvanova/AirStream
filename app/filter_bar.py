from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLineEdit

from app.accessibility import set_accessible_props


class FilterBar(QWidget):
    filters_changed = Signal(str, str, str)  # name, countrycode, tag

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.country_combo = QComboBox()
        self.country_combo.addItem("All Countries", "")
        set_accessible_props(
            self.country_combo,
            "Country filter",
            "Select a country to filter stations",
        )

        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All Genres", "")
        set_accessible_props(
            self.genre_combo,
            "Genre filter",
            "Select a genre to filter stations",
        )

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search stations...")
        set_accessible_props(
            self.search_field,
            "Search stations",
            "Type to search stations by name",
        )

        layout.addWidget(self.country_combo, 1)
        layout.addWidget(self.genre_combo, 1)
        layout.addWidget(self.search_field, 2)

        # Debounce timer for search
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._emit_filters)

        self.country_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.genre_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.search_field.textChanged.connect(self._on_text_changed)

    def populate_countries(self, countries):
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        self.country_combo.addItem("All Countries", "")
        for c in countries:
            name = c.get("name", "")
            code = c.get("iso_3166_1", "")
            count = c.get("stationcount", 0)
            self.country_combo.addItem(f"{name} ({count})", code)
        self.country_combo.blockSignals(False)

    def populate_genres(self, tags):
        self.genre_combo.blockSignals(True)
        self.genre_combo.clear()
        self.genre_combo.addItem("All Genres", "")
        for t in tags:
            name = t.get("name", "")
            count = t.get("stationcount", 0)
            self.genre_combo.addItem(f"{name} ({count})", name)
        self.genre_combo.blockSignals(False)

    def _on_filter_changed(self):
        self._emit_filters()

    def _on_text_changed(self):
        self._debounce.start()

    def _emit_filters(self):
        name = self.search_field.text().strip()
        country = self.country_combo.currentData() or ""
        tag = self.genre_combo.currentData() or ""
        self.filters_changed.emit(name, country, tag)

    def current_filters(self):
        return (
            self.search_field.text().strip(),
            self.country_combo.currentData() or "",
            self.genre_combo.currentData() or "",
        )
