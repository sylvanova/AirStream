import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Internet Radio")
    app.setOrganizationName("InternetRadio")

    window = MainWindow()
    window.show()
    logging.info("Window shown, ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
