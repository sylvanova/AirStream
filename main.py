import sys
import logging

_frozen = getattr(sys, "frozen", False)
_handlers = [logging.StreamHandler(sys.stderr)]
if not _frozen:
    _handlers.append(logging.FileHandler("debug.log", mode="w", encoding="utf-8"))
logging.basicConfig(
    level=logging.WARNING if _frozen else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AirStream")
    app.setOrganizationName("AirStream")

    window = MainWindow()
    window.show()
    logging.info("Window shown, ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
