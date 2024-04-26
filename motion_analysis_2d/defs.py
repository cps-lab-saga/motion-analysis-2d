import os
import platform
import subprocess
from pathlib import Path

project_name = "motion-analysis-2d"
app_version = "0.1.7"

module_name = project_name.replace("-", "_")


try:
    from PySide6 import QtGui, QtWidgets, QtCore, QtWebEngineWidgets
    from PySide6.QtCore import Signal, Slot

    backend_name = "pyside6"

except ModuleNotFoundError:
    try:
        from PyQt6 import QtGui, QtWidgets, QtCore, QtWebEngineWidgets
        from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

        backend_name = "pyqt6"

    except ModuleNotFoundError:
        from PyQt5 import QtGui, QtWidgets, QtCore
        from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

        backend_name = "pyqt5"


def config_dir() -> Path:
    d = Path.home() / f".{project_name}"
    d.mkdir(exist_ok=True)
    return d


def project_root() -> Path:
    Path(__file__).parent.parent.mkdir(exist_ok=True, parents=True)
    return Path(__file__).parent.parent


def ui_file() -> Path:
    return config_dir() / "ma2d_ui_restore.ini"


def shortcuts_file():
    return config_dir() / "ma2d_shortcuts.json"


def visual_preferences_file():
    return config_dir() / "ma2d_visual.json"


def log_file() -> Path:
    return config_dir() / f"{project_name}.log"


def resource_dir() -> Path:
    return project_root() / module_name / "resource"


def readme_file() -> Path:
    return project_root() / "README.md"


def open_file(file_path):
    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", file_path))
    elif platform.system() == "Windows":  # Windows
        os.startfile(file_path)
    else:  # linux variants
        subprocess.call(("xdg-open", file_path))
    os.startfile(file_path)
