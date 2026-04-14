from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStatusBar,
    QLineEdit,
)

from app.accessibility import announce, set_accessible_props
from app.filter_bar import FilterBar
from app.station_list import StationListView
from app.player_controls import PlayerControls
from app.favorites_dialog import AddStationDialog, FavoritesDialog
from services.audio_player import AudioPlayer
from services import radio_api, storage


class ApiWorker(QObject):
    stations_loaded = Signal(list)
    countries_loaded = Signal(list)
    tags_loaded = Signal(list)
    favorites_loaded = Signal(list, list)  # favorite stations, custom stations
    error = Signal(str)

    @Slot()
    def fetch_initial(self):
        try:
            stations = radio_api.fetch_top_stations()
            self.stations_loaded.emit(stations)
        except Exception as e:
            self.error.emit(str(e))

        try:
            countries = radio_api.fetch_countries()
            self.countries_loaded.emit(countries)
        except Exception:
            pass

        try:
            tags = radio_api.fetch_tags()
            self.tags_loaded.emit(tags)
        except Exception:
            pass

    @Slot(str, str, str)
    def search(self, name, countrycode, tag):
        try:
            stations = radio_api.search_stations(name, countrycode, tag)
            self.stations_loaded.emit(stations)
        except Exception as e:
            self.error.emit(str(e))

    @Slot()
    def fetch_favorites(self):
        fav_uuids = storage.get_favorites()
        custom = storage.get_custom_stations()
        fav_stations = []
        if fav_uuids:
            try:
                fav_stations = radio_api.fetch_stations_by_uuid(fav_uuids)
            except Exception:
                pass
        self.favorites_loaded.emit(fav_stations, custom)


class MainWindow(QMainWindow):
    _request_search = Signal(str, str, str)
    _request_initial = Signal()
    _request_favorites = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Internet Radio")
        self.setMinimumSize(700, 500)

        self._player = AudioPlayer(self)
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_worker()
        self._load_initial_data()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Filter bar
        self.filter_bar = FilterBar()
        layout.addWidget(self.filter_bar)

        # Station list
        self.station_list = StationListView()
        layout.addWidget(self.station_list, 1)

        # Player controls
        self.player_controls = PlayerControls(self._player)
        layout.addWidget(self.player_controls)

        # Action buttons
        action_layout = QHBoxLayout()
        self.fav_view_btn = QPushButton("View Favorites")
        set_accessible_props(self.fav_view_btn, "View favorites")
        self.add_station_btn = QPushButton("Add Custom Station")
        set_accessible_props(self.add_station_btn, "Add custom station")

        action_layout.addWidget(self.fav_view_btn)
        action_layout.addWidget(self.add_station_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Loading stations...")

        # Connect signals
        self.filter_bar.filters_changed.connect(self._on_filters_changed)
        self.station_list.station_activated.connect(self._on_station_activated)
        self.player_controls.fav_button.clicked.connect(self._on_fav_clicked)
        self.fav_view_btn.clicked.connect(self._on_view_favorites)
        self.add_station_btn.clicked.connect(self._on_add_station)

        # Update favorite button when selection changes
        self.station_list.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        # Explicit tab order: country → genre → search → station list → fav → play → view fav → add station
        QWidget.setTabOrder(self.filter_bar.country_combo, self.filter_bar.genre_combo)
        QWidget.setTabOrder(self.filter_bar.genre_combo, self.filter_bar.search_field)
        QWidget.setTabOrder(self.filter_bar.search_field, self.station_list)
        QWidget.setTabOrder(self.station_list, self.player_controls.fav_button)
        QWidget.setTabOrder(self.player_controls.fav_button, self.player_controls.play_button)
        QWidget.setTabOrder(self.player_controls.play_button, self.fav_view_btn)
        QWidget.setTabOrder(self.fav_view_btn, self.add_station_btn)

    def _setup_shortcuts(self):
        # Alt+F to toggle favorite
        self._fav_shortcut = QShortcut(QKeySequence("Alt+F"), self)
        self._fav_shortcut.activated.connect(self._on_fav_clicked)

        # Escape to stop
        self._stop_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._stop_shortcut.activated.connect(self._on_stop)

    def keyPressEvent(self, event):
        # Space to toggle play/pause — but only when not in a text input
        if event.key() == Qt.Key.Key_Space:
            focused = self.focusWidget()
            if not isinstance(focused, (QLineEdit,)):
                self._on_space_pressed()
                event.accept()
                return
        super().keyPressEvent(event)

    def _setup_worker(self):
        self._worker_thread = QThread()
        self._worker = ApiWorker()
        self._worker.moveToThread(self._worker_thread)

        self._worker.stations_loaded.connect(self._on_stations_loaded)
        self._worker.countries_loaded.connect(self._on_countries_loaded)
        self._worker.tags_loaded.connect(self._on_tags_loaded)
        self._worker.favorites_loaded.connect(self._on_favorites_loaded)
        self._worker.error.connect(self._on_api_error)

        self._request_initial.connect(self._worker.fetch_initial)
        self._request_search.connect(self._worker.search)
        self._request_favorites.connect(self._worker.fetch_favorites)

        self._worker_thread.start()

    def _load_initial_data(self):
        self._request_initial.emit()

    def _on_stations_loaded(self, stations):
        if stations:
            storage.save_cached_stations(stations)
        else:
            # Try cache if API returned nothing
            cached = storage.get_cached_stations()
            if cached:
                stations = cached
                self.status_bar.showMessage(
                    f"Offline — showing {len(stations)} cached stations"
                )
                self.station_list.set_stations(stations)
                announce(self, f"Offline mode. Showing {len(stations)} cached stations")
                return

        self.station_list.set_stations(stations)
        count = self.station_list.station_count()
        self.status_bar.showMessage(f"{count} stations loaded")
        announce(self, f"{count} stations loaded")
        self.station_list.setFocus()

    def _on_countries_loaded(self, countries):
        self.filter_bar.populate_countries(countries)

    def _on_tags_loaded(self, tags):
        self.filter_bar.populate_genres(tags)

    def _on_favorites_loaded(self, fav_stations, custom_stations):
        dlg = FavoritesDialog(fav_stations, custom_stations, self)
        if dlg.exec() == FavoritesDialog.DialogCode.Accepted:
            station = dlg.selected_station()
            if station:
                self._on_station_activated(station)
        self.fav_view_btn.setFocus()

    def _on_api_error(self, message):
        self.status_bar.showMessage(f"Error: {message}")
        announce(self, f"Error loading stations: {message}")

        # Try cached stations
        cached = storage.get_cached_stations()
        if cached:
            self.station_list.set_stations(cached)
            count = len(cached)
            self.status_bar.showMessage(
                f"Offline — showing {count} cached stations"
            )

    def _on_filters_changed(self, name, countrycode, tag):
        if not name and not countrycode and not tag:
            self._request_initial.emit()
        else:
            self._request_search.emit(name, countrycode, tag)
        self.status_bar.showMessage("Searching...")

    def _on_station_activated(self, station):
        self.player_controls.play_station(station)
        self._update_fav_button_for(station)

    def _on_selection_changed(self):
        station = self.station_list.selected_station()
        if station:
            self.player_controls.set_station(station)
            self._update_fav_button_for(station)

    def _on_space_pressed(self):
        # Space only toggles play/pause — does not start a new station
        self.player_controls.toggle_pause()

    def _on_stop(self):
        self._player.stop()
        self.player_controls.now_playing_label.setText("Not playing")
        set_accessible_props(self.player_controls.now_playing_label, "Not playing")
        announce(self, "Playback stopped")

    def _on_fav_clicked(self):
        station = (
            self.player_controls.current_station()
            or self.station_list.selected_station()
        )
        if not station:
            return
        uuid = station.get("stationuuid", "")
        if not uuid:
            return
        if storage.is_favorite(uuid):
            storage.remove_favorite(uuid)
            self.player_controls.update_favorite_button(False)
            announce(self, f"{station.get('name', '')} removed from favorites")
        else:
            storage.add_favorite(uuid)
            self.player_controls.update_favorite_button(True)
            announce(self, f"{station.get('name', '')} added to favorites")

    def _update_fav_button_for(self, station):
        uuid = station.get("stationuuid", "")
        is_fav = storage.is_favorite(uuid) if uuid else False
        self.player_controls.update_favorite_button(is_fav)

    def _on_view_favorites(self):
        self._request_favorites.emit()

    def _on_add_station(self):
        dlg = AddStationDialog(self)
        if dlg.exec() == AddStationDialog.DialogCode.Accepted:
            station = storage.add_custom_station(dlg.station_name(), dlg.station_url())
            announce(self, f"Custom station {station['name']} added")
            self.status_bar.showMessage(f"Added custom station: {station['name']}")
        self.add_station_btn.setFocus()

    def closeEvent(self, event):
        self._player.cleanup()
        self._worker_thread.quit()
        self._worker_thread.wait(2000)
        super().closeEvent(event)
