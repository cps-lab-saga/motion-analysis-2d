from defs import QtCore, QtWidgets, QtGui
from motion_analysis_2d.custom_components import ColorButton, tab10_rgb


class TrackerDialog(QtWidgets.QDialog):
    def __init__(
        self,
        default_name="",
        default_color=tab10_rgb["green"],
        default_tracker_type="CSRT",
    ):
        super().__init__()

        self.name = default_name
        self.color = default_color
        self.tracker_type = default_tracker_type
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        self.resize(60, 10)
        self.setWindowTitle("Add Tracker")
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.form_layout = QtWidgets.QFormLayout(self)
        self.main_layout.addLayout(self.form_layout)

        self.name_edit = QtWidgets.QLineEdit(self)
        validator = QtGui.QRegularExpressionValidator(r"^$|[\-\w]+$")
        self.name_edit.setValidator(validator)
        self.name_edit.setText(self.name)
        self.name_edit.returnPressed.connect(self.completed)
        self.form_layout.addRow("Name: ", self.name_edit)

        self.tracking_combobox = QtWidgets.QComboBox(self)
        self.tracking_combobox.addItems(
            [
                "CSRT",
                "MedianFlow",
                "KCF",
                "Boosting",
                "MOSSE",
                "MIL",
                "Static",
            ]
        )
        self.tracking_combobox.setCurrentText(self.tracker_type)
        self.form_layout.addRow("Tracker: ", self.tracking_combobox)

        self.color_button = ColorButton(self)
        self.color_button.set_default_color("green")
        self.color_button.set_rbg(self.color)
        self.form_layout.addRow("Colour: ", self.color_button)

        self.main_layout.addStretch()

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.completed)
        self.main_layout.addWidget(self.ok_button)

        self.main_layout.addStretch()

    def completed(self):
        self.name = self.name_edit.text()
        self.color = self.color_button.get_rgb()
        self.tracker_type = self.tracking_combobox.currentText()
        self.accept()
        self.close()

    def get_inputs(self):
        return self.name, self.color, self.tracker_type


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    dialog = TrackerDialog()
    dialog.show()

    app.exec()
