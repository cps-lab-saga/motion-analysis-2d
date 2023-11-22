import logging
from pathlib import Path

import cv2 as cv
import numpy as np
import qtawesome as qta

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock, PathEdit
from motion_analysis_2d.funcs import load_extrinsic


class LoadExtrinsicDock(BaseDock):
    settings_updated = Signal()
    select_points_started = Signal()
    select_points_finished = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Warp Perspective")

        self.cal_ok = False
        self.M, self.mask, self.output_size, self.scaling = None, None, None, 1

        row = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(row)
        self.extrinsic_cal_file_edit = PathEdit("file", self)
        self.extrinsic_cal_file_edit.acceptDrops()
        self.extrinsic_cal_file_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.extrinsic_cal_file_edit.textChanged.connect(self.update_extrinsic_cal)
        self.extrinsic_cal_file_edit.setToolTip("Calibration file path.")
        row.addWidget(self.extrinsic_cal_file_edit)

        self.dir_button = QtWidgets.QPushButton(self)
        self.dir_button.setText("…")
        self.dir_button.setFlat(True)
        self.dir_button.setMaximumWidth(20)
        self.dir_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dir_button.clicked.connect(self.set_dir)
        self.dir_button.setToolTip("Get calibration file.")
        row.addWidget(self.dir_button)

        self.icon_size = 18
        self.cal_status_label = QtWidgets.QLabel(self)
        self.cross_icon = qta.icon("mdi.close-circle", color="red")
        self.tick_icon = qta.icon("mdi.check-circle", color="green")
        self.cal_status_label.setPixmap(self.cross_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration unsuccessful.")
        row.insertWidget(0, self.cal_status_label)

        self.select_points_button = QtWidgets.QPushButton(self)
        # self.select_points_button.setText("Select Points")
        self.select_points_button.setToolTip("Select calibration points from frame.")
        self.select_points_button.setFlat(True)
        self.select_points_button.setCheckable(True)
        self.select_points_button.setIcon(qta.icon("mdi6.cursor-default-click"))
        self.select_points_button.toggled.connect(self.select_points_button_toggled)
        row.addWidget(self.select_points_button)

        self.dock_layout.addStretch()

    def set_dir(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if file_name:
            self.extrinsic_cal_file_edit.setText(file_name)

    def set_cal_ok(self):
        self.cal_ok = True
        self.cal_status_label.setPixmap(self.tick_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration successful.")

    def set_cal_bad(self):
        self.cal_ok = False
        self.cal_status_label.setPixmap(self.cross_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration unsuccessful.")

        self.M, self.mask, self.output_size, self.scaling = None, None, None, 1

    def update_extrinsic_cal(self):
        try:
            file_name = self.extrinsic_cal_file_edit.text()
            self.M, self.mask, self.output_size, self.scaling = load_extrinsic(
                Path(file_name).resolve()
            )
            self.set_cal_ok()
            logging.info(f"Extrinsic calibration load successful. File: {file_name}")
            if self.M is not None:
                logging_repr = (
                    lambda x: np.array_repr(x).replace(" ", "").replace("\n", " ")
                )
                logging.info(f"M: {logging_repr(self.M)}")
                logging.info(f"output_size: {logging_repr(self.output_size)}")
            logging.info(f"scaling: {self.scaling}")

        except Exception as e:
            self.set_cal_bad()
            logging.warning(f"Extrinsic calibration load unsuccessful. {e}")
        self.settings_updated.emit()

    def change_perspective(self, img):
        if self.M is not None:
            return (
                cv.warpPerspective(img, self.M, self.output_size)
                if self.cal_ok
                else img
            )
        else:
            return img

    def select_points_button_toggled(self, checked):
        if checked:
            self.extrinsic_cal_file_edit.setText("")
            self.select_points_started.emit()
        else:
            self.select_points_finished.emit()

    def uncheck_select_points_button(self):
        self.select_points_button.blockSignals(True)
        self.select_points_button.setChecked(False)
        self.select_points_button.blockSignals(False)

    def gui_save(self, settings):
        self.uncheck_select_points_button()
        super().gui_save(settings)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = LoadExtrinsicDock()
    widget.show()

    app.exec()
