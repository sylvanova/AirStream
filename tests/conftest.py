import pytest

from PySide6.QtCore import QCoreApplication


@pytest.fixture(scope="session")
def qapp():
    """Provide a QCoreApplication for tests that touch Qt signals."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app
