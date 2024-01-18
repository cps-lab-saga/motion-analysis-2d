from defs import QtCore, QtWidgets, Signal


class PerspectiveDialog(QtWidgets.QDialog):
    completed = Signal(float, float)

    def __init__(self, title="Adjust perspective"):
        super().__init__()

        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.x_distance = None
        self.y_distance = None

        self.resize(60, 10)
        self.setWindowTitle(title)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.form_layout = QtWidgets.QFormLayout(self)
        self.main_layout.addLayout(self.form_layout)

        self.x_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.x_spinbox.setRange(0, 10**5)
        self.x_spinbox.setDecimals(3)
        self.x_spinbox.setValue(0)
        self.x_spinbox.setSpecialValueText("Auto")
        self.form_layout.addRow("X: ", self.x_spinbox)

        self.y_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.y_spinbox.setRange(0, 10**5)
        self.y_spinbox.setDecimals(3)
        self.y_spinbox.setValue(0)
        self.y_spinbox.setSpecialValueText("Auto")
        self.form_layout.addRow("Y: ", self.y_spinbox)

        self.main_layout.addStretch()

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.ok_clicked)
        self.main_layout.addWidget(self.ok_button)

        self.main_layout.addStretch()

    def ok_clicked(self):
        self.x_distance = self.x_spinbox.value()
        self.y_distance = self.y_spinbox.value()
        self.completed.emit(self.x_distance, self.y_distance)

        self.accept()
        self.close()

    def get_result(self):
        return self.x_distance, self.y_distance


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    dialog = PerspectiveDialog()
    dialog.show()

    app.exec()
