from functools import partial

import qtawesome as qta
from PySide6 import QtCore

from defs import QtWidgets, Signal
from motion_analysis_2d.custom_components import BadgeButton, tab10_qcolor


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
            "Add Tracker", "add_tracker", qta.icon("mdi6.vector-rectangle"), "+", "blue"
        )
        self.add_button(
            "Remove Tracker",
            "remove_tracker",
            qta.icon("mdi6.vector-rectangle"),
            "−",
            "red",
        )
        # self.add_button(
        #     "Add Vector", "add_vector", qta.icon("mdi6.vector-line"), "+", "blue"
        # )
        # self.add_button(
        #     "Remove Vector",
        #     "remove_vector",
        #     qta.icon("mdi6.vector-line"),
        #     "−",
        #     "red",
        # )
        self.add_button(
            "Add Angle", "add_angle", qta.icon("mdi6.angle-acute"), "+", "blue"
        )
        self.add_button(
            "Remove Angle", "remove_angle", qta.icon("mdi6.angle-acute"), "−", "red"
        )
        self.add_button(
            "Add Distance", "add_distance", qta.icon("mdi6.ruler"), "+", "blue"
        )
        self.add_button(
            "Remove Distance", "remove_distance", qta.icon("mdi6.ruler"), "−", "red"
        )

        self.main_layout.addStretch()

    def add_button(
        self,
        label,
        mode,
        icon,
        badge_text,
        color="blue",
        icon_size=24,
        badge_size=8,
        point_size=12,
    ):
        button = BadgeButton(
            badge_size, tab10_qcolor[color], "white", point_size, parent=self
        )
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
