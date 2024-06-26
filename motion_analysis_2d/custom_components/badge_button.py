from motion_analysis_2d.defs import QtCore, QtWidgets, QtGui


class BadgeButton(QtWidgets.QWidget):
    def __init__(
        self,
        badge_size,
        badge_color,
        badge_text_color,
        point_size=None,
        parent=None,
    ):
        super().__init__(parent)

        self.badge_size = badge_size
        self.badge_color = badge_color
        self.badge_text_color = badge_text_color
        self.point_size = point_size

        lay = QtWidgets.QVBoxLayout(self)
        self.button = QtWidgets.QPushButton(self)
        lay.addWidget(self.button)
        self.badge = QtWidgets.QLabel(self.button)
        self.badge.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setContentsMargins(0, 0, 0, 0)
        lay.setContentsMargins(0, 0, 0, 0)

        for m in [
            "setIcon",
            "setIconSize",
            "setFlat",
            "click",
            "clicked",
            "setCheckable",
            "isChecked",
            "setChecked",
            "toggle",
            "toggled",
        ]:
            setattr(self, m, getattr(self.button, m))

    def set_badge(self, text):
        self.badge.setPixmap(
            create_badge_pixmap(
                text,
                self.badge_size,
                self.badge_color,
                self.badge_text_color,
                self.point_size,
            )
        )
        self.badge.adjustSize()

    def set_no_badge(self):
        self.badge.setPixmap(
            create_badge_pixmap(
                "",
                self.badge_size,
                "transparent",
                "transparent",
                self.point_size,
            ),
        )
        self.badge.adjustSize()

    def resizeEvent(self, event):
        self.badge.move(
            self.width() - self.badge.width(), self.height() - self.badge.height()
        )
        super().resizeEvent(event)


def create_badge_pixmap(text, radius, badge_color, badge_text_color, point_size=None):
    rect = QtCore.QRect(0, 0, radius * 2, radius * 2)
    pixmap = QtGui.QPixmap(rect.size())
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHints(
        QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing
    )
    painter.setBrush(QtGui.QBrush(QtGui.QColor(badge_color)))
    if point_size is None:
        painter.setFont(
            QtGui.QFont("Arial", round(radius * 0.8), QtGui.QFont.ExtraBold)
        )
    else:
        painter.setFont(QtGui.QFont("Arial", point_size, QtGui.QFont.ExtraBold))

    text_pen = QtGui.QPen()
    text_pen.setColor(QtGui.QColor(badge_text_color))

    painter.setPen(QtCore.Qt.NoPen)
    painter.drawEllipse(rect)
    painter.setPen(text_pen)
    painter.drawText(rect, QtCore.Qt.AlignCenter, text)
    painter.end()
    return pixmap


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = BadgeButton(8, "red", "white")
    widget.set_badge("test")
    widget.show()

    app.exec()
