"""
Build script for AirStream.
Usage: python build.py [windows|macos|linux]
Defaults to current platform if no argument given.
"""

import subprocess
import sys
import platform


def build_windows():
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--windowed", "--onefile",
        "--collect-data", "certifi",
        "--name", "AirStream",
        "main.py",
    ], check=True)
    print("\nBuild complete: dist/AirStream.exe")


def build_macos():
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--windowed",
        "--collect-data", "certifi",
        "--target-arch", "universal2",
        "--name", "AirStream",
        "--osx-bundle-identifier", "com.airstream.app",
        "main.py",
    ], check=True)
    print("\nBuild complete: dist/AirStream.app")


def build_linux():
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onefile",
        "--collect-data", "certifi",
        "--name", "AirStream",
        "main.py",
    ], check=True)
    print("\nBuild complete: dist/AirStream")


def main():
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
    else:
        system = platform.system().lower()
        target = {"windows": "windows", "darwin": "macos", "linux": "linux"}.get(system, system)

    builders = {
        "windows": build_windows,
        "macos": build_macos,
        "mac": build_macos,
        "linux": build_linux,
    }

    if target not in builders:
        print(f"Unknown target: {target}")
        print(f"Usage: python build.py [windows|macos|linux]")
        sys.exit(1)

    print(f"Building AirStream for {target}...")
    builders[target]()


if __name__ == "__main__":
    main()
