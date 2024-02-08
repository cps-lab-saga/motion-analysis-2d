import logging
from pathlib import Path

import cv2 as cv
import numpy as np
import qtawesome as qta
from camera_calibration import CalibrationWidget

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock, PathEdit
from motion_analysis_2d.funcs import get_undistort_funcs, load_intrinsic


class LoadIntrinsicDock(BaseDock):
    settings_updated = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lens Distortion")

        self.cal_ok = False
        self.K = None
        self.D = None
        self.map_x, self.map_y, self.new_K = None, None, None
        self.img_shape = None

        row = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(row)
        self.intrinsic_cal_file_edit = PathEdit("file", self)
        self.intrinsic_cal_file_edit.acceptDrops()
        self.intrinsic_cal_file_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.intrinsic_cal_file_edit.textChanged.connect(self.update_intrinsic_cal)
        self.intrinsic_cal_file_edit.setToolTip("Calibration file path.")
        row.addWidget(self.intrinsic_cal_file_edit)

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

        self.add_calibration_button = QtWidgets.QPushButton(self)
        # self.select_points_button.setText("Select Points")
        self.add_calibration_button.setToolTip("Add calibration.")
        self.add_calibration_button.setFlat(True)
        self.add_calibration_button.setIcon(qta.icon("mdi6.checkerboard"))
        self.add_calibration_button.clicked.connect(self.start_calibration_widget)
        row.addWidget(self.add_calibration_button)

        self.dock_layout.addStretch()

    def set_dir(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if file_name:
            self.intrinsic_cal_file_edit.setText(file_name)

    def set_cal_ok(self):
        self.cal_ok = True
        self.cal_status_label.setPixmap(self.tick_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration successful.")

    def set_cal_bad(self):
        self.cal_ok = False
        self.cal_status_label.setPixmap(self.cross_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration unsuccessful.")

        self.K = None
        self.D = None
        self.map_x, self.map_y, self.new_K = None, None, None

    def set_image_shape(self, shape):
        self.img_shape = shape
        self.update_intrinsic_cal()

    def update_intrinsic_cal(self):
        try:
            file_name = self.intrinsic_cal_file_edit.text()
            self.K, self.D = load_intrinsic(Path(file_name).resolve())
            self.set_cal_ok()
            if self.img_shape is not None:
                self.map_x, self.map_y, self.new_K = get_undistort_funcs(
                    self.img_shape, self.K, self.D, fisheye=True
                )
            logging.info(f"Intrinsic calibration load successful. File: {file_name}")
            logging_repr = (
                lambda x: np.array_repr(x).replace(" ", "").replace("\n", " ")
            )
            logging.info(f"K: {logging_repr(self.K)}")
            logging.info(f"D: {logging_repr(self.D)}")
            if self.img_shape is not None:
                logging.info(f"new_K: {logging_repr(self.new_K)}")

        except Exception as e:
            self.set_cal_bad()
            logging.warning(f"Intrinsic calibration load unsuccessful. {e}")
        self.settings_updated.emit()

    def undistort_map(self, img):
        if not self.cal_ok:
            return img
        if self.img_shape is None:
            self.set_image_shape(img.shape)

        return cv.remap(img, self.map_x, self.map_y, cv.INTER_LINEAR)

    def undistort_points(self, points):
        if self.cal_ok:
            return cv.undistortPoints(points, self.K, self.D, None, self.new_K)
        else:
            return points

    def redistort_points(self, points):
        if not self.cal_ok:
            return points

        scaled_points = np.vstack(
            [
                (points[:, 0] - self.new_K[0, 2]) / self.new_K[0, 0],
                (points[:, 1] - self.new_K[1, 2]) / self.new_K[1, 1],
                np.zeros(points.shape[0]),
            ]
        ).T
        distorted_points, _ = cv.projectPoints(
            scaled_points,
            np.zeros(3),
            np.zeros(3),
            self.K,
            self.D,
            aspectRatio=self.new_K[0, 0] / self.new_K[1, 1],
        )
        return distorted_points

    def start_calibration_widget(self):
        calibration_widget = CalibrationWidget(self)
        calibration_widget.calibration_saved.connect(self.calibration_widget_finished)
        calibration_widget.show()

    def calibration_widget_finished(self, path):
        self.intrinsic_cal_file_edit.setText(str(path))


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = LoadIntrinsicDock()
    widget.show()

    app.exec()
