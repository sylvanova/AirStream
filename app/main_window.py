import logging

from PySide6.QtCore import Qt, QThread, QObject, QEvent, Signal, Slot
from PySide6.QtGui import QShortcut, QKeySequence

log = logging.getLogger(__name__)
import time

from PySide6.QtWidgets import (
    QApplication,
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
from app.station_list import StationListView, StationButton
from app.player_controls import PlayerControls
from app.favorites_dialog import AddStationDialog, FavoritesDialog
from services.audio_player import AudioPlayer
from services import radio_api, storage


class ApiWorker(QObject):
    stations_loaded = Signal(list)
    countries_loaded = Signal(list)
    tags_loaded = Signal(list)
    favorites_rehydrated = Signal(list)
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

    @Slot(list)
    def rehydrate_favorites(self, uuids):
        if not uuids:
            return
        try:
            stations = radio_api.fetch_stations_by_uuid(uuids)
            self.favorites_rehydrated.emit(stations)
        except Exception as e:
            log.warning("favorite rehydrate failed: %s", e)


class MainWindow(QMainWindow):
    _request_search = Signal(str, str, str)
    _request_initial = Signal()
    _request_rehydrate = Signal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirStream")
        self.setMinimumSize(700, 500)

        self._player = AudioPlayer(self)
        self._initial_load = True
        self._is_searching = False
        self._combo_cooldown = 0  # kept for compatibility
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_worker()
        self._load_initial_data()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Filter bar (adds its widgets directly to layout)
        self.filter_bar = FilterBar(layout, parent=self)

        # Station list
        self.station_list = StationListView()
        layout.addWidget(self.station_list, 1)

        # Player controls (adds its widgets directly to layout)
        self.player_controls = PlayerControls(self._player, layout, parent=self)

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
        self.player_controls.fav_button.clicked.connect(lambda: log.debug("BUTTON CLICK: fav_button"))
        self.player_controls.fav_button.clicked.connect(self._on_fav_clicked)
        self.player_controls.play_button.clicked.connect(lambda: log.debug("BUTTON CLICK: play_button"))
        self.fav_view_btn.clicked.connect(lambda: log.debug("BUTTON CLICK: fav_view_btn"))
        self.fav_view_btn.clicked.connect(self._on_view_favorites)
        self.add_station_btn.clicked.connect(lambda: log.debug("BUTTON CLICK: add_station_btn"))
        self.add_station_btn.clicked.connect(self._on_add_station)

        # Update favorite button when a station gets focus
        self.station_list.station_activated.connect(
            lambda s: self._update_fav_button_for(s)
        )

        # Explicit tab order: country → genre → search → station list → fav → play → view fav → add station
        QWidget.setTabOrder(self.filter_bar.country_button, self.filter_bar.genre_button)
        QWidget.setTabOrder(self.filter_bar.genre_button, self.filter_bar.search_field)
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

        # Install app-wide event filter
        QApplication.instance().installEventFilter(self)

        # Log focus changes to debug Tab navigation
        QApplication.instance().focusChanged.connect(self._on_focus_changed)

    def _on_focus_changed(self, old, new):
        old_name = f"{type(old).__name__}({old.accessibleName()})" if old else "None"
        new_name = f"{type(new).__name__}({new.accessibleName()})" if new else "None"
        log.debug(f"Focus: {old_name} -> {new_name}")
        # Track which station is selected when focus moves between station buttons
        if isinstance(new, StationButton):
            for i, btn in enumerate(self.station_list._buttons):
                if btn is new:
                    self.station_list._current_index = i
                    self.player_controls.set_station(new.station)
                    self._update_fav_button_for(new.station)
                    break

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            # Log key events for debugging
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and modifiers != Qt.KeyboardModifier.NoModifier:
                log.debug(f"Arrow key={key} modifiers={modifiers}")
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space, Qt.Key.Key_Tab):
                focused = QApplication.focusWidget()
                log.debug(f"Key {key} on {type(focused).__name__ if focused else 'None'} (obj={type(obj).__name__})")

            # Consume bare modifier keys on station buttons to prevent focus jumping
            if key in (Qt.Key.Key_Control, Qt.Key.Key_Meta):
                focused = QApplication.focusWidget()
                if isinstance(focused, StationButton):
                    return True

            # Arrow keys navigate within the station list (skip if Ctrl/Cmd held for volume)
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up) and not (modifiers & Qt.KeyboardModifier.ControlModifier or modifiers & Qt.KeyboardModifier.MetaModifier):
                focused = QApplication.focusWidget()
                if isinstance(focused, StationButton):
                    sl = self.station_list
                    if key == Qt.Key.Key_Down:
                        new_idx = min(sl._current_index + 1, len(sl._buttons) - 1)
                    else:
                        new_idx = max(sl._current_index - 1, 0)
                    if new_idx != sl._current_index:
                        sl._current_index = new_idx
                        sl._focus_current()
                    return True

            # Tab on a station button exits the station list
            if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                focused = QApplication.focusWidget()
                if isinstance(focused, StationButton):
                    self.player_controls.fav_button.setFocus()
                    return True

            # Shift+Tab on a station button goes back to search
            if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.ShiftModifier:
                focused = QApplication.focusWidget()
                if isinstance(focused, StationButton):
                    # Go back, but use backtab which is the actual key
                    self.filter_bar.search_field.setFocus()
                    return True
            if key == Qt.Key.Key_Backtab:
                focused = QApplication.focusWidget()
                if isinstance(focused, StationButton):
                    self.filter_bar.search_field.setFocus()
                    return True

            # Make Enter activate focused buttons
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                focused = QApplication.focusWidget()
                if isinstance(focused, QPushButton):
                    log.debug(f"Enter activating button: {focused.accessibleName()}")
                    focused.click()
                    return True

            # Space = play/pause ALWAYS, except in the search field
            if key == Qt.Key.Key_Space and modifiers == Qt.KeyboardModifier.NoModifier:
                focused = QApplication.focusWidget()
                if isinstance(focused, QLineEdit):
                    return False  # let search field type a space
                log.debug(f"Space -> play/pause (focused={type(focused).__name__ if focused else 'None'})")
                self._on_space_pressed()
                return True

            ctrl_held = modifiers & Qt.KeyboardModifier.ControlModifier or modifiers & Qt.KeyboardModifier.MetaModifier
            if ctrl_held:
                if key == Qt.Key.Key_P:
                    log.debug("Ctrl+P: toggle play/pause")
                    self._on_space_pressed()
                    return True
                if key == Qt.Key.Key_B:
                    log.debug("Ctrl+B: toggle favorite")
                    self._on_fav_clicked()
                    return True
                if key == Qt.Key.Key_L:
                    log.debug("Ctrl+L: view favorites")
                    self._on_view_favorites()
                    return True
                if key == Qt.Key.Key_N:
                    log.debug("Ctrl+N: add custom station")
                    self._on_add_station()
                    return True
                if key == Qt.Key.Key_F:
                    log.debug("Ctrl+F: focus search")
                    self.filter_bar.search_field.setFocus()
                    self.filter_bar.search_field.selectAll()
                    return True
                if key == Qt.Key.Key_Up:
                    self._volume_up()
                    return True
                if key == Qt.Key.Key_Down:
                    self._volume_down()
                    return True

        return super().eventFilter(obj, event)

    def _setup_worker(self):
        self._worker_thread = QThread()
        self._worker = ApiWorker()
        self._worker.moveToThread(self._worker_thread)

        self._worker.stations_loaded.connect(self._on_stations_loaded)
        self._worker.countries_loaded.connect(self._on_countries_loaded)
        self._worker.tags_loaded.connect(self._on_tags_loaded)
        self._worker.favorites_rehydrated.connect(self._on_favorites_rehydrated)
        self._worker.error.connect(self._on_api_error)

        self._request_initial.connect(self._worker.fetch_initial)
        self._request_search.connect(self._worker.search)
        self._request_rehydrate.connect(self._worker.rehydrate_favorites)

        self._worker_thread.start()

        pending = storage.pending_favorite_uuids()
        if pending:
            self._request_rehydrate.emit(pending)

    def _load_initial_data(self):
        self._request_initial.emit()

    def _on_stations_loaded(self, stations):
        if stations:
            if not self._is_searching:
                storage.save_cached_stations(stations)
        elif not self._is_searching:
            # Only fall back to cache on initial load, not searches
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
        if self._is_searching:
            self._is_searching = False
            if count == 0:
                self.status_bar.showMessage("No stations found")
                announce(self, "No stations found")
            else:
                self.status_bar.showMessage(f"Found {count} stations")
                announce(self, f"Found {count} stations")
        else:
            self.status_bar.showMessage(f"{count} stations loaded")
            announce(self, f"{count} stations loaded")
        # Only grab focus on first load, not when filtering
        if self._initial_load:
            self.station_list.setFocus()
            self._initial_load = False

    def _on_countries_loaded(self, countries):
        self.filter_bar.populate_countries(countries)

    def _on_tags_loaded(self, tags):
        self.filter_bar.populate_genres(tags)

    def _on_favorites_rehydrated(self, stations):
        storage.update_favorites_with_stations(stations)

    def _show_favorites_dialog(self, fav_stations, custom_stations):
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
        self._is_searching = True
        if not name and not countrycode and not tag:
            self._is_searching = False
            self._request_initial.emit()
        else:
            self._request_search.emit(name, countrycode, tag)
        self.status_bar.showMessage("Searching...")

    def _on_station_activated(self, station):
        log.info(f"Playing: {station.get('name')} — {station.get('url_resolved', station.get('url', ''))}")
        self.player_controls.play_station(station)
        self._update_fav_button_for(station)

    def _on_selection_changed(self):
        station = self.station_list.selected_station()
        if station:
            self.player_controls.set_station(station)
            self._update_fav_button_for(station)

    def _on_space_pressed(self):
        log.debug(f"toggle_pause: player state={self._player._last_state}, paused={self._player._paused}, url={self._player._current_url}")
        self.player_controls.toggle_pause()

    def _volume_up(self):
        vol = self._player.volume()
        new_vol = min(100, vol + 10)
        self._player.set_volume(new_vol)
        announce(self, f"Volume {new_vol} percent")
        self.status_bar.showMessage(f"Volume: {new_vol}%", 2000)

    def _volume_down(self):
        vol = self._player.volume()
        new_vol = max(0, vol - 10)
        self._player.set_volume(new_vol)
        announce(self, f"Volume {new_vol} percent")
        self.status_bar.showMessage(f"Volume: {new_vol}%", 2000)

    def _on_stop(self):
        self._player.stop()
        self.player_controls.now_playing_label.setText("Not playing")
        set_accessible_props(self.player_controls.now_playing_label, "Not playing")
        announce(self, "Playback stopped")

    def _on_fav_clicked(self):
        cur = self.player_controls.current_station()
        sel = self.station_list.selected_station()
        station = cur or sel
        log.debug(f"fav_clicked: current={cur.get('name') if cur else None}, selected={sel.get('name') if sel else None}")
        if not station:
            log.debug("fav_clicked: no station available")
            self.status_bar.showMessage("No station selected")
            announce(self, "No station selected")
            return
        uuid = station.get("stationuuid", "")
        if not uuid:
            return
        if storage.is_favorite(uuid):
            storage.remove_favorite(uuid)
            self.player_controls.update_favorite_button(False)
            announce(self, f"{station.get('name', '')} removed from favorites")
        else:
            storage.add_favorite(station)
            self.player_controls.update_favorite_button(True)
            announce(self, f"{station.get('name', '')} added to favorites")

    def _update_fav_button_for(self, station):
        uuid = station.get("stationuuid", "")
        is_fav = storage.is_favorite(uuid) if uuid else False
        self.player_controls.update_favorite_button(is_fav)

    def _on_view_favorites(self):
        # Favorites store the full station dict, so no cross-reference needed.
        fav_stations = storage.get_favorites()
        custom = storage.get_custom_stations()
        self._show_favorites_dialog(fav_stations, custom)

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
