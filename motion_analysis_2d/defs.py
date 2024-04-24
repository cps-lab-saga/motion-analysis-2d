import os
import platform
import subprocess
from pathlib import Path

project_name = "motion-analysis-2d"
app_version = "0.1.6"

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


def project_root() -> Path:
    Path(__file__).parent.parent.mkdir(exist_ok=True, parents=True)
    return Path(__file__).parent.parent


def settings_file(file_name) -> Path:
    p = project_root()
    if "Temp" in p.parts:
        f = (
            p.parents[len(p.parts) - 2 - p.parts.index("Temp")]
            / f"{project_name}"
            / file_name
        )
    else:
        f = project_root() / file_name

    f.parent.mkdir(exist_ok=True, parents=True)
    return f


def shortcuts_file():
    return settings_file("ma2d_shortcuts.json")


def visual_preferences_file():
    return settings_file("ma2d_visual.json")


def log_file() -> Path:
    return Path.cwd() / f"{project_name}.log"


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


config_file_name = f"{project_name}-config.ini"
