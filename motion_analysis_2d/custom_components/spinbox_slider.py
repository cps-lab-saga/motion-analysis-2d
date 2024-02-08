from motion_analysis_2d.defs import QtCore, QtWidgets, Signal


class SpinBoxSlider(QtWidgets.QWidget):
    valueChanged = Signal(int)
    valueChangeFinished = Signal(int)

    def __init__(self, orientation="horizontal", parent=None, **kargs):
        super().__init__(parent=parent)

        if orientation == "horizontal":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.LeftToRight, self
            )
            self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, **kargs, parent=self)
        elif orientation == "vertical":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.TopToBottom, self
            )
            self.slider = QtWidgets.QSlider(QtCore.Qt.Vertical, **kargs, parent=self)
        else:
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.TopToBottom, self
            )
            self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, **kargs, parent=self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.slider.valueChanged.connect(self.emitValueChanged)
        self.slider.sliderReleased.connect(self.emitValueChangeFinished)

        self.spinbox = QtWidgets.QSpinBox(self)
        self.spinbox.valueChanged.connect(self.emitValueChanged)
        self.spinbox.editingFinished.connect(self.emitValueChangeFinished)

        self.main_layout.addWidget(self.slider)
        self.main_layout.addWidget(self.spinbox)

    def emitValueChanged(self):
        value = self.match_values(self.sender())
        self.valueChanged.emit(value)

    def emitValueChangeFinished(self):
        value = self.match_values(self.sender())
        self.valueChangeFinished.emit(value)

    def match_values(self, sender):
        if sender == self.slider:
            value = self.slider.value()
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(value)
            self.spinbox.blockSignals(False)
        else:
            value = self.spinbox.value()
            self.slider.blockSignals(True)
            self.slider.setValue(value)
            self.slider.blockSignals(False)
        return value

    def value(self):
        return self.slider.value()

    def setMinimum(self, value):
        self.slider.setMinimum(value)
        self.spinbox.setMinimum(value)

    def setMaximum(self, value):
        self.slider.setMaximum(value)
        self.spinbox.setMaximum(value)

    def setRange(self, min_value, max_value):
        self.slider.setRange(min_value, max_value)
        self.spinbox.setRange(min_value, max_value)

    def setSingleStep(self, value):
        self.slider.setSingleStep(value)
        self.spinbox.setSingleStep(value)

    def setValue(self, value):
        self.slider.setValue(value)
        self.spinbox.setValue(value)
        self.valueChangeFinished.emit(value)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = SpinBoxSlider("horizontal")
    widget.setRange(0, 100)
    widget.show()

    app.exec()
