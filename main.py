import sys
import logging

LOG_FILE = "debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
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
