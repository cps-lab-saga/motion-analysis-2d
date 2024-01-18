from pathlib import Path

project_name = "motion-analysis-2d"
app_version = "0.1.1"

module_name = project_name.replace("-", "_")

try:
    from PySide6 import QtGui, QtWidgets, QtCore
    from PySide6.QtCore import Signal, Slot

    backend_name = "pyside6"

except ModuleNotFoundError:
    try:
        from PyQt6 import QtGui, QtWidgets, QtCore
        from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

        backend_name = "pyqt6"

    except ModuleNotFoundError:
        from PyQt5 import QtGui, QtWidgets, QtCore
        from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

        backend_name = "pyqt5"


def project_root() -> Path:
    Path(__file__).parent.mkdir(exist_ok=True, parents=True)
    return Path(__file__).parent


def settings_file() -> Path:
    p = project_root()
    if "Temp" in p.parts:
        f = (
            p.parents[len(p.parts) - 2 - p.parts.index("Temp")]
            / f"{project_name}"
            / f"{project_name}.ini"
        )
    else:
        f = project_root() / f"{project_name}.ini"

    f.parent.mkdir(exist_ok=True, parents=True)
    return f


def shortcut_keys_file() -> Path:
    p = project_root()
    if "Temp" in p.parts:
        f = (
            p.parents[len(p.parts) - 2 - p.parts.index("Temp")]
            / f"{project_name}"
            / f"{project_name}.ini"
        )
    else:
        f = project_root() / f"{project_name}.ini"

    f.parent.mkdir(exist_ok=True, parents=True)
    return f


def log_file() -> Path:
    return Path.cwd() / f"{project_name}.log"


def resource_dir() -> Path:
    return project_root() / "resource"


config_file_name = f"{project_name}-config.ini"
