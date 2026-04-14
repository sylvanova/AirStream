from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QWidget, QLabel

# Dedicated hidden label for screen reader announcements
_live_region = None


def _get_live_region():
    global _live_region
    if _live_region is None:
        _live_region = QLabel()
        _live_region.setVisible(False)
        _live_region.setAccessibleName("")
    return _live_region


def announce(widget, message):
    """Send a screen reader announcement without moving focus."""
    if not QAccessible.isActive():
        return
    try:
        from PySide6.QtGui import QAccessibleAnnouncementEvent
        event = QAccessibleAnnouncementEvent(widget, message)
        QAccessible.updateAccessibility(event)
    except (ImportError, AttributeError):
        # Fallback: update a hidden label's accessible name
        region = _get_live_region()
        # Toggle name to ensure NameChanged fires even for repeated messages
        region.setAccessibleName("")
        event_clear = QAccessibleEvent(region, QAccessible.Event.NameChanged)
        QAccessible.updateAccessibility(event_clear)
        region.setAccessibleName(message)
        event = QAccessibleEvent(region, QAccessible.Event.NameChanged)
        QAccessible.updateAccessibility(event)


def set_accessible_props(widget, name, description=""):
    """Set accessible name and optional description on a widget."""
    widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)
