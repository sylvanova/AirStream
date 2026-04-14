from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QWidget


def announce(widget, message):
    """Send a screen reader announcement without moving focus."""
    if not QAccessible.isActive():
        return
    try:
        event = QAccessible.AnnouncementEvent(widget, message)
        QAccessible.updateAccessibility(event)
    except AttributeError:
        # Fallback for PySide6 < 6.8: fire a NameChanged event
        widget.setAccessibleName(message)
        event = QAccessibleEvent(widget, QAccessible.Event.NameChanged)
        QAccessible.updateAccessibility(event)


def set_accessible_props(widget, name, description=""):
    """Set accessible name and optional description on a widget."""
    widget.setAccessibleName(name)
    if description:
        widget.setAccessibleDescription(description)
