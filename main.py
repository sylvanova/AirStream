import sys

from PySide6.QtWidgets import QApplication, QMessageBox


def check_vlc():
    """Check if VLC is installed and available."""
    try:
        import vlc
        instance = vlc.Instance("--no-video")
        instance.release()
        return True
    except (OSError, Exception):
        return False


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Internet Radio")
    app.setOrganizationName("InternetRadio")

    if not check_vlc():
        QMessageBox.critical(
            None,
            "VLC Required",
            "VLC media player is required but was not found.\n\n"
            "Please install VLC from:\n"
            "https://www.videolan.org/vlc/\n\n"
            "Then restart this application.",
        )
        sys.exit(1)

    from app.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
