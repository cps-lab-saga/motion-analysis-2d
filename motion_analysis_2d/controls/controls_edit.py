from functools import partial

import qtawesome as qta
from PySide6 import QtCore

from motion_analysis_2d.custom_components import BadgeButton, tab10_qcolor
from motion_analysis_2d.defs import QtWidgets, Signal


class EditControls(QtWidgets.QFrame):
    mode_changed = Signal(str)

    def __init__(self, parent=None, orientation="horizontal"):
        super().__init__(parent=parent)

        self.setWindowTitle("Edit")
        # self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        if orientation == "horizontal":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.LeftToRight, self
            )
        elif orientation == "vertical":
            self.main_layout = QtWidgets.QBoxLayout(
                QtWidgets.QBoxLayout.TopToBottom, self
            )

        self.buttons = []

        self.add_button(
            "Add Tracker",
            "add_tracker",
            qta.icon("mdi6.vector-rectangle"),
            badge_text="+",
        )
        self.add_button(
            "Add Angle", "add_angle", qta.icon("mdi6.angle-acute"), badge_text="+"
        )
        self.add_button(
            "Add Distance", "add_distance", qta.icon("mdi6.ruler"), badge_text="+"
        )
        self.add_button(
            "Remove",
            "remove_item",
            qta.icon("ei.remove", color=tab10_qcolor["red"]),
            icon_size=20,
        )

        self.main_layout.addStretch()

    def add_button(
        self,
        label,
        mode,
        icon,
        icon_size=24,
        badge_text=None,
        badge=None,
    ):
        if badge is None:
            badge = {
                "badge_size": 8,
                "badge_color": tab10_qcolor["blue"],
                "badge_text_color": "white",
                "point_size": 12,
            }
        if badge_text is None:
            button = QtWidgets.QPushButton(parent=self)
        else:
            button = BadgeButton(**badge, parent=self)
            button.set_badge(badge_text)
        button.setToolTip(label)
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(icon_size, icon_size))
        button.setFlat(True)
        button.setCheckable(True)
        button.toggled.connect(partial(self.button_toggled, button, mode))
        self.main_layout.addWidget(button)
        self.buttons.append(button)

    def button_toggled(self, sender, mode, checked):
        if not checked:
            self.mode_changed.emit("normal")
        else:
            for button in self.buttons:
                if button.isChecked() and button is not sender:
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
            self.mode_changed.emit(mode)

    def set_normal_mode(self):
        self.mode_changed.emit("normal")
        for button in self.buttons:
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = EditControls()
    widget.show()

    app.exec()
