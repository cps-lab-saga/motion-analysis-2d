from defs import QtCore, QtWidgets


class PointDialog(QtWidgets.QDialog):
    def __init__(self, img_point, title="Add Point"):
        super().__init__()

        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.point = None
        self.finish = False

        self.resize(60, 10)
        self.setWindowTitle(title)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.form_layout = QtWidgets.QFormLayout(self)
        self.main_layout.addLayout(self.form_layout)

        self.x_label = QtWidgets.QLabel(f"{img_point[0]}", self)
        self.form_layout.addRow("Image X: ", self.x_label)

        self.y_label = QtWidgets.QLabel(f"{img_point[1]}", self)
        self.form_layout.addRow("Image Y: ", self.y_label)

        self.x_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.x_spinbox.setRange(-(10**5), 10**5)
        self.x_spinbox.setSuffix(" m")
        self.form_layout.addRow("Real X: ", self.x_spinbox)

        self.y_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.y_spinbox.setRange(-(10**5), 10**5)
        self.y_spinbox.setSuffix(" m")
        self.form_layout.addRow("Real Y: ", self.y_spinbox)

        self.main_layout.addStretch()

        self.finish_checkbox = QtWidgets.QCheckBox("Finish", self)
        self.main_layout.addWidget(self.finish_checkbox)

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.completed)
        self.main_layout.addWidget(self.ok_button)

        self.main_layout.addStretch()

    def completed(self):
        self.point = (self.x_spinbox.value(), self.y_spinbox.value())
        self.finish = self.finish_checkbox.isChecked()

        self.accept()
        self.close()

    def get_result(self):
        return self.point, self.finish


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    dialog = PointDialog((0, 0))
    dialog.show()

    app.exec()
