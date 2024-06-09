import logging
from itertools import cycle

import cv2 as cv
import qtawesome as qta

from motion_analysis_2d.custom_components import BaseDock, BadgeButton, tab10_qcolor
from motion_analysis_2d.defs import QtCore, QtWidgets, Signal


class OrientDock(BaseDock):
    orient_settings_updated = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Orientation")

        self.rot_cycle = cycle(["0", "90", "180", "270"])
        self.flip_cycle = cycle(["no_flip", "h_flip", "v_flip", "hv_flip"])
        self.rotation = next(self.rot_cycle)
        self.flip = next(self.flip_cycle)

        self.orientation_layout = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(self.orientation_layout)
        self.orientation_layout.addStretch()

        icon_size = 30
        badge_size = 8
        self.rotate_button = BadgeButton(
            badge_size, tab10_qcolor["red"], "white", parent=self
        )
        self.rotate_icons = {
            "0": qta.icon("mdi.camera-retake", rotated=0, hflip=True),
            "90": qta.icon("mdi.camera-retake", rotated=90, hflip=True),
            "180": qta.icon("mdi.camera-retake", rotated=180, hflip=True),
            "270": qta.icon("mdi.camera-retake", rotated=270, hflip=True),
        }
        self.rotate_tooltips = {
            "0": "Rotate frame.",
            "90": "Rotated by 90 degrees.",
            "180": "Rotated by 180 degrees.",
            "270": "Rotated by 270 degrees.",
        }
        self.rotate_button.setIcon(self.rotate_icons[self.rotation])
        self.rotate_button.setToolTip(self.rotate_tooltips[self.rotation])
        self.rotate_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.rotate_button.setFlat(True)
        self.rotate_button.set_no_badge()
        self.rotate_button.clicked.connect(self.rotate_button_clicked)
        self.orientation_layout.addWidget(self.rotate_button)
        self.orientation_layout.addStretch()

        self.flip_button = BadgeButton(
            badge_size, tab10_qcolor["blue"], "white", parent=self
        )
        self.flip_icons = {
            "no_flip": qta.icon("mdi6.flip-horizontal"),
            "h_flip": qta.icon("mdi6.reflect-horizontal"),
            "v_flip": qta.icon("mdi6.reflect-vertical"),
            "hv_flip": qta.icon(
                "mdi6.reflect-horizontal",
                "mdi6.reflect-vertical",
                options=[
                    {"scale_factor": 0.7, "offset": (-0.2, 0)},
                    {"scale_factor": 0.7, "offset": (0.2, 0)},
                ],
            ),
        }
        self.flip_tooltips = {
            "no_flip": "Flip frame.",
            "h_flip": "Flipped horizontally.",
            "v_flip": "Flipped vertically.",
            "hv_flip": "Flipped horizontally and vertically.",
        }

        self.flip_button.setIcon(self.flip_icons[self.flip])
        self.flip_button.setToolTip(self.flip_tooltips[self.flip])
        self.flip_button.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.flip_button.setFlat(True)
        self.flip_button.set_no_badge()
        self.flip_button.clicked.connect(self.flip_button_clicked)
        self.orientation_layout.addWidget(self.flip_button)
        self.orientation_layout.addStretch()

        self.dock_layout.addStretch()

    def rotate_button_clicked(self):
        self.rotation = next(self.rot_cycle)
        self.update_rotate_button()
        logging.info(f"Rotation changed to {self.rotation}")
        self.orient_settings_updated.emit(self.flip, self.rotation)

    def update_rotate_button(self):
        self.rotate_button.setIcon(self.rotate_icons[self.rotation])
        self.rotate_button.setToolTip(self.rotate_tooltips[self.rotation])
        if self.rotation == "0":
            self.rotate_button.set_no_badge()
        else:
            self.rotate_button.set_badge(self.rotation)

    def flip_button_clicked(self):
        self.flip = next(self.flip_cycle)
        self.update_flip_button()
        logging.info(f"Flip changed to {self.flip}")
        self.orient_settings_updated.emit(self.flip, self.rotation)

    def update_flip_button(self):
        self.flip_button.setIcon(self.flip_icons[self.flip])
        self.flip_button.setToolTip(self.flip_tooltips[self.flip])
        if self.flip == "no_flip":
            self.flip_button.set_no_badge()
        else:
            self.flip_button.set_badge("✱")

    def rotate_img(self, img):
        settings = self.rotation
        if settings == "0":
            return img
        elif settings == "90":
            return cv.rotate(img, cv.ROTATE_90_CLOCKWISE)
        elif settings == "180":
            return cv.rotate(img, cv.ROTATE_180)
        elif settings == "270":
            return cv.rotate(img, cv.ROTATE_90_COUNTERCLOCKWISE)

    def flip_img(self, img):
        settings = self.flip
        if settings == "no_flip":
            return img
        elif settings == "h_flip":
            return cv.flip(img, 1)
        elif settings == "v_flip":
            return cv.flip(img, 0)
        elif settings == "hv_flip":
            return cv.flip(img, -1)

    def gui_save(self, settings):
        settings.setValue(f"{self.save_heading}/rotate_settings", self.rotation)
        settings.setValue(f"{self.save_heading}/flip_settings", self.flip)

    def gui_restore(self, settings):
        rotation = settings.value(f"{self.save_heading}/rotate_settings")
        self.restore_rotation(rotation)

        flip = settings.value(f"{self.save_heading}/flip_settings")
        self.restore_flip(flip)

    def restore_rotation(self, rotation):
        if rotation in self.rotate_icons.keys():
            while self.rotation != rotation:
                self.rotation = next(self.rot_cycle)
            self.update_rotate_button()

    def restore_flip(self, flip):
        if flip in self.flip_icons.keys():
            while self.flip != flip:
                self.flip = next(self.flip_cycle)
            self.update_flip_button()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = OrientDock()
    widget.show()

    app.exec()
