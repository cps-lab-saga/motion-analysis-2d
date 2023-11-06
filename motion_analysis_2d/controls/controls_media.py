import qtawesome as qta
from PySide6 import QtCore

from defs import QtWidgets, Signal
from motion_analysis_2d.custom_components import SpinBoxSlider


class MediaControls(QtWidgets.QFrame):
    play = Signal(bool)
    previous_frame = Signal()
    next_frame = Signal()
    seek_bar_moved = Signal(int)

    def __init__(self, parent=None, orientation="horizontal"):
        super().__init__(parent=parent)

        self.setWindowTitle("Media")
        # self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

        if orientation == "horizontal":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.LeftToRight, self
            )
        elif orientation == "vertical":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.TopToBottom, self
            )

        icon_size = 24
        self.play_button = QtWidgets.QPushButton(self)
        self.play_button.setToolTip("Play")
        self.play_icon = qta.icon("mdi6.play")
        self.pause_icon = qta.icon("mdi6.pause")
        self.play_button.setIcon(self.play_icon)
        self.play_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.play_button.setFlat(True)
        self.play_button.setCheckable(True)
        self.play_button.toggled.connect(self.play_button_toggled)
        self.main_layout.addWidget(self.play_button)

        self.seek_bar = SpinBoxSlider(orientation, self)
        self.seek_bar.spinbox.setPrefix("Frame ")
        self.seek_bar.setSingleStep(1)
        self.seek_bar.setMinimum(0)
        self.seek_bar.valueChanged.connect(self.seek_bar_moved.emit)
        self.main_layout.addWidget(self.seek_bar)

        icon_size = 16
        self.previous_button = QtWidgets.QPushButton(self.seek_bar)
        self.previous_button.setToolTip("Previous Frame")
        self.previous_button.setIcon(qta.icon("mdi6.step-backward"))
        self.previous_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.previous_button.setFlat(True)
        self.previous_button.clicked.connect(self.previous_frame.emit)
        self.seek_bar.main_layout.insertWidget(1, self.previous_button)

        self.next_button = QtWidgets.QPushButton(self.seek_bar)
        self.next_button.setToolTip("Next Frame")
        self.next_button.setIcon(qta.icon("mdi6.step-forward"))
        self.next_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.next_button.setFlat(True)
        self.next_button.clicked.connect(self.next_frame.emit)
        self.seek_bar.main_layout.insertWidget(2, self.next_button)

    def play_button_toggled(self):
        if self.play_button.isChecked():
            self.play_button.setIcon(self.pause_icon)
            self.seek_bar.setDisabled(True)
            self.play.emit(True)
        else:
            self.play_button.setIcon(self.play_icon)
            self.seek_bar.setDisabled(False)
            self.play.emit(False)

    def pause(self):
        self.blockSignals(True)
        self.play_button.setChecked(False)
        self.blockSignals(False)
        self.play.emit(False)

    def set_seeking_props(self, no_of_frames):
        self.seek_bar.setMaximum(no_of_frames)

    def set_seek_bar_value(self, value):
        self.blockSignals(True)
        self.seek_bar.setValue(value)
        self.blockSignals(False)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = MediaControls()
    widget.show()

    app.exec()
