from pathlib import Path

import qtawesome as qta

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock


class SaveDock(BaseDock):
    autosave_toggled = Signal(bool)
    export_clicked = Signal(Path)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Save Data")

        row = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(row)

        icon_size = 18
        self.autosave_button = QtWidgets.QPushButton(self)
        self.autosave_button.setIcon(qta.icon("mdi6.content-save-settings"))
        self.autosave_button.setText("Auto Save")
        self.autosave_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.autosave_button.setToolTip("Auto save data.")
        self.autosave_button.setCheckable(True)
        self.autosave_button.setFlat(True)
        self.autosave_button.toggled.connect(self.autosave_button_toggled)
        row.addWidget(self.autosave_button)

        self.export_button = QtWidgets.QPushButton(self)
        self.export_button.setIcon(qta.icon("mdi6.file-export"))
        self.export_button.setText("Export")
        self.export_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.export_button.setToolTip("Export data.")
        self.export_button.setFlat(True)
        self.export_button.clicked.connect(self.export_button_clicked)
        row.addWidget(self.export_button)

    def autosave_button_toggled(self):
        self.autosave_toggled.emit(self.autosave_button.isChecked())

    def export_button_clicked(self):
        path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export", None, "CSV (*.csv)"
        )
        if path[1] == "CSV (*.csv)":
            export_path = Path(path[0]).resolve()
            self.export_clicked.emit(export_path)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = SaveDock()
    widget.show()

    app.exec()
