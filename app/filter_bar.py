from PySide6.QtCore import Qt, QObject, QTimer, QEvent, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLineEdit,
    QDialog, QVBoxLayout, QGroupBox, QScrollArea, QWidget, QSizePolicy,
    QApplication,
)

from app.accessibility import set_accessible_props, announce


class _PickerButton(QPushButton):
    """Button inside a picker dialog, for type checking in the event filter."""
    pass


class PickerDialog(QDialog):
    """Accessible dialog for picking from a list of options."""

    def __init__(self, title, options, current_value, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 350)
        self._selected_value = current_value
        self._buttons = []
        self._current_index = 0

        layout = QVBoxLayout(self)

        group = QGroupBox(title)
        set_accessible_props(group, title)
        group.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        group_layout.addWidget(self._scroll)

        container = QWidget()
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(1)

        for i, (label, value) in enumerate(options):
            btn = _PickerButton(label)
            set_accessible_props(btn, label)
            btn.setFlat(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 6px 8px; border: none; }"
                "QPushButton:focus { background: palette(highlight); color: palette(highlighted-text); }"
            )
            btn.clicked.connect(lambda checked, v=value, l=label: self._pick(v, l))
            self._list_layout.addWidget(btn)
            self._buttons.append(btn)
            if value == current_value:
                self._current_index = i

        self._list_layout.addStretch()
        self._scroll.setWidget(container)
        layout.addWidget(group, 1)

        self._cancel_btn = QPushButton("Cancel")
        set_accessible_props(self._cancel_btn, "Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self._cancel_btn)

        QApplication.instance().installEventFilter(self)

        if self._buttons:
            self._focus_current()

        QTimer.singleShot(200, lambda: announce(self, title))

    def _focus_current(self):
        if self._buttons and 0 <= self._current_index < len(self._buttons):
            btn = self._buttons[self._current_index]
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setFocus()
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._scroll.ensureWidgetVisible(btn)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            focused = QApplication.focusWidget()
            key = event.key()
            modifiers = event.modifiers()

            if isinstance(focused, _PickerButton):
                if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                    if key == Qt.Key.Key_Down:
                        new_idx = min(self._current_index + 1, len(self._buttons) - 1)
                    else:
                        new_idx = max(self._current_index - 1, 0)
                    if new_idx != self._current_index:
                        self._current_index = new_idx
                        self._focus_current()
                    return True

                if key == Qt.Key.Key_Tab and modifiers == Qt.KeyboardModifier.NoModifier:
                    self._cancel_btn.setFocus()
                    return True
                if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and modifiers == Qt.KeyboardModifier.ShiftModifier:
                    self._cancel_btn.setFocus()
                    return True
                if key == Qt.Key.Key_Backtab:
                    self._cancel_btn.setFocus()
                    return True

                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    focused.click()
                    return True

        return super().eventFilter(obj, event)

    def _pick(self, value, label):
        self._selected_value = value
        self._selected_label = label
        self.accept()

    def selected_value(self):
        return self._selected_value

    def selected_label(self):
        return getattr(self, '_selected_label', '')


class FilterBar(QObject):
    filters_changed = Signal(str, str, str)  # name, countrycode, tag

    def __init__(self, parent_layout, parent=None):
        super().__init__(parent)
        self._parent_widget = parent

        self._countries = []  # list of (label, code) tuples
        self._genres = []     # list of (label, name) tuples
        self._current_country = ""
        self._current_genre = ""

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.country_button = QPushButton("Country: All")
        set_accessible_props(self.country_button, "Country: All")
        self.country_button.clicked.connect(self._open_country_picker)

        self.genre_button = QPushButton("Genre: All")
        set_accessible_props(self.genre_button, "Genre: All")
        self.genre_button.clicked.connect(self._open_genre_picker)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search stations...")
        set_accessible_props(self.search_field, "Search")

        layout.addWidget(self.country_button, 1)
        layout.addWidget(self.genre_button, 1)
        layout.addWidget(self.search_field, 2)

        parent_layout.addLayout(layout)

        # Debounce timer for search
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._emit_filters)

        self.search_field.textChanged.connect(self._on_text_changed)

    def populate_countries(self, countries):
        self._countries = [("All Countries", "")]
        for c in countries:
            name = c.get("name", "")
            code = c.get("iso_3166_1", "")
            count = c.get("stationcount", 0)
            self._countries.append((f"{name} ({count})", code))

    def populate_genres(self, tags):
        self._genres = [("All Genres", "")]
        for t in tags:
            name = t.get("name", "")
            count = t.get("stationcount", 0)
            self._genres.append((f"{name} ({count})", name))

    def _open_country_picker(self):
        if not self._countries:
            return
        dlg = PickerDialog("Country", self._countries, self._current_country, self._parent_widget)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._current_country = dlg.selected_value()
            label = dlg.selected_label()
            short = label.split(" (")[0] if " (" in label else label
            self.country_button.setText(f"Country: {short}")
            set_accessible_props(self.country_button, f"Country: {short}")
            self._emit_filters()
        self.country_button.setFocus()

    def _open_genre_picker(self):
        if not self._genres:
            return
        dlg = PickerDialog("Genre", self._genres, self._current_genre, self._parent_widget)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._current_genre = dlg.selected_value()
            label = dlg.selected_label()
            short = label.split(" (")[0] if " (" in label else label
            self.genre_button.setText(f"Genre: {short}")
            set_accessible_props(self.genre_button, f"Genre: {short}")
            self._emit_filters()
        self.genre_button.setFocus()

    def _on_text_changed(self):
        self._debounce.start()

    def _emit_filters(self):
        name = self.search_field.text().strip()
        country = self._current_country
        tag = self._current_genre
        new_filters = (name, country, tag)
        if hasattr(self, '_last_filters') and new_filters == self._last_filters:
            return
        self._last_filters = new_filters
        self.filters_changed.emit(name, country, tag)

    def current_filters(self):
        return (
            self.search_field.text().strip(),
            self._current_country,
            self._current_genre,
        )
