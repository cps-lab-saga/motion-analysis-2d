from defs import QtWidgets, QtGui, Signal

from motion_analysis_2d.custom_components.my_colors import tab10_qcolor


class ColorButton(QtWidgets.QPushButton):
    color_changed = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._q_color = QtGui.QColor(0, 0, 0)
        self.color_dialog = QtWidgets.QColorDialog(self)
        for i, qcolor in enumerate(tab10_qcolor):
            self.color_dialog.setCustomColor(i, qcolor)

        self.setStyleSheet(
            f"background-color: rgb{self._q_color.getRgb()[:3]};" f"border-radius: 5px;"
        )
        self.clicked.connect(self.color_button_clicked)

    def set_default_color(self, color):
        if color in tab10_qcolor:
            self.color_dialog.setCurrentColor(tab10_qcolor[color])
        elif isinstance(color, QtGui.QColor):
            self.color_dialog.setCurrentColor(color)
        else:
            self.color_dialog.setCurrentColor(QtGui.QColor(*color))

    def color_button_clicked(self):
        color = self.color_dialog.getColor()
        if color.isValid():
            self.set_rbg(color.getRgb()[:3])
            self.color_changed.emit(self.get_rgb())

    def get_rgbf(self):
        return self._q_color.getRgbF()[:3]

    def set_rgbf(self, color_rgbf):
        self._q_color = QtGui.QColor(*color_rgbf)
        self.setStyleSheet(
            f"background-color: rgb{self._q_color.getRgb()[:3]};" f"border-radius: 5px;"
        )

    def get_rgb(self):
        return self._q_color.getRgb()[:3]

    def set_rbg(self, color_rgb):
        self._q_color = QtGui.QColor(*color_rgb)
        self.setStyleSheet(
            f"background-color: rgb{self._q_color.getRgb()[:3]};" f"border-radius: 5px;"
        )


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = ColorButton()
    widget.show()

    app.exec()
