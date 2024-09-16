from qtpy import QtCore, QtWidgets


class PerspectiveDialog(QtWidgets.QDialog):
    mode_changed = QtCore.Signal(str)
    completed = QtCore.Signal(str, tuple)

    def __init__(self, title="Adjust Perspective / Scaling"):
        super().__init__()

        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.x_distance = None
        self.y_distance = None
        self.length = None

        self.resize(300, 10)
        self.setWindowTitle(title)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.mode_combobox = QtWidgets.QComboBox(self)
        self.mode_combobox.addItems(["Perspective", "Scaling"])
        self.mode_combobox.activated.connect(self.switch_page)
        self.main_layout.addWidget(self.mode_combobox)

        self.stacked_layout = QtWidgets.QStackedLayout()
        self.main_layout.addLayout(self.stacked_layout)

        self.perspective_page = QtWidgets.QWidget(self)
        self.perspective_form_layout = QtWidgets.QFormLayout(self.perspective_page)
        self.stacked_layout.addWidget(self.perspective_page)

        self.x_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.x_spinbox.setRange(0, 10**5)
        self.x_spinbox.setDecimals(3)
        self.x_spinbox.setValue(0)
        self.x_spinbox.setSpecialValueText("Auto")
        self.perspective_form_layout.addRow("X: ", self.x_spinbox)

        self.y_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.y_spinbox.setRange(0, 10**5)
        self.y_spinbox.setDecimals(3)
        self.y_spinbox.setValue(0)
        self.y_spinbox.setSpecialValueText("Auto")
        self.perspective_form_layout.addRow("Y: ", self.y_spinbox)

        self.scaling_page = QtWidgets.QWidget(self)
        self.scaling_form_layout = QtWidgets.QFormLayout(self.scaling_page)
        self.stacked_layout.addWidget(self.scaling_page)

        self.length_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.length_spinbox.setRange(0, 10**5)
        self.length_spinbox.setDecimals(3)
        self.length_spinbox.setValue(1)
        self.scaling_form_layout.addRow("Length: ", self.length_spinbox)

        self.main_layout.addStretch()

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.ok_clicked)
        self.main_layout.addWidget(self.ok_button)

        self.main_layout.addStretch()

    def switch_page(self):
        self.stacked_layout.setCurrentIndex(self.mode_combobox.currentIndex())
        self.mode_changed.emit(self.mode())

    def mode(self):
        return self.mode_combobox.currentText()

    def ok_clicked(self):
        self.x_distance = self.x_spinbox.value()
        self.y_distance = self.y_spinbox.value()
        self.length = self.length_spinbox.value()
        mode = self.mode_combobox.currentText()
        if mode == "Perspective":
            self.completed.emit(mode, (self.x_distance, self.y_distance))
        elif mode == "Scaling":
            self.completed.emit(mode, (self.length,))

        self.accept()
        self.close()

    def get_result(self):
        return self.x_distance, self.y_distance


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    dialog = PerspectiveDialog()
    dialog.show()

    app.exec()
