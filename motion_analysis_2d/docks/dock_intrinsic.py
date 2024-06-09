import logging
from pathlib import Path

import numpy as np
import qtawesome as qta
from camera_calibration import CalibrationWidget

from motion_analysis_2d.custom_components import BaseDock, PathEdit
from motion_analysis_2d.defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.funcs import (
    get_undistort_funcs,
    load_intrinsic,
    undistort_map,
)


class LoadIntrinsicDock(BaseDock):
    intrinsic_settings_updated = Signal(bool, object, object)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lens Distortion")

        self.cal_ok = False
        self.K = None
        self.D = None
        self.fisheye = None
        self.map_x, self.map_y, self.new_K = None, None, None
        self.frame_shape = None
        self.mutex = QtCore.QMutex()

        grid = QtWidgets.QGridLayout()
        self.dock_layout.addLayout(grid)

        self.icon_size = 18
        self.cal_status_label = QtWidgets.QLabel(self)
        self.cross_icon = qta.icon("mdi.close-circle", color="red")
        self.tick_icon = qta.icon("mdi.check-circle", color="green")
        self.cal_status_label.setPixmap(self.cross_icon.pixmap(self.icon_size))
        self.cal_status_label.setToolTip("Calibration unsuccessful.")
        grid.addWidget(self.cal_status_label, 0, 0)

        self.intrinsic_cal_file_edit = PathEdit("file", self)
        self.intrinsic_cal_file_edit.acceptDrops()
        self.intrinsic_cal_file_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.intrinsic_cal_file_edit.textChanged.connect(self.update_intrinsic_cal)
        self.intrinsic_cal_file_edit.setToolTip("Calibration file path.")
        grid.addWidget(self.intrinsic_cal_file_edit, 0, 1)

        self.dir_button = QtWidgets.QPushButton(self)
        self.dir_button.setText("…")
        self.dir_button.setFlat(True)
        self.dir_button.setMaximumWidth(20)
        self.dir_button.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dir_button.clicked.connect(self.set_dir)
        self.dir_button.setToolTip("Get calibration file.")
        grid.addWidget(self.dir_button, 0, 2)

        self.scale_spinbox = QtWidgets.QDoubleSpinBox(self)
        self.scale_spinbox.setRange(0.1, 2.0)
        self.scale_spinbox.setDecimals(1)
        self.scale_spinbox.setSingleStep(0.1)
        self.scale_spinbox.setValue(1)
        self.scale_spinbox.valueChanged.connect(self.update_intrinsic_cal)
        grid.addWidget(self.scale_spinbox, 1, 1)

        self.add_calibration_button = QtWidgets.QPushButton(self)
        # self.select_points_button.setText("Select Points")
        self.add_calibration_button.setToolTip("Add calibration.")
        self.add_calibration_button.setFlat(True)
        self.add_calibration_button.setIcon(qta.icon("mdi6.checkerboard"))
        self.add_calibration_button.clicked.connect(self.start_calibration_widget)
        grid.addWidget(self.add_calibration_button, 0, 3)

        self.dock_layout.addStretch()

    def set_dir(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if file_name:
            self.intrinsic_cal_file_edit.blockSignals(True)
            self.intrinsic_cal_file_edit.setText(file_name)
            self.intrinsic_cal_file_edit.blockSignals(False)
            self.update_intrinsic_cal()

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
        self.fisheye = None

        self.map_x, self.map_y, self.new_K = None, None, None

    def set_frame_shape(self, shape):
        self.frame_shape = shape
        self.update_intrinsic_cal()

    @property
    def scale(self):
        return self.scale_spinbox.value()

    def update_intrinsic_cal(self):
        self.mutex.lock()
        try:
            file_name = self.intrinsic_cal_file_edit.text()
            self.K, self.D, self.fisheye = load_intrinsic(Path(file_name).resolve())
            self.set_cal_ok()
            if self.frame_shape is not None:
                self.map_x, self.map_y, self.new_K = get_undistort_funcs(
                    self.frame_shape, self.K, self.D, self.fisheye, self.scale
                )
            logging.info(f"Intrinsic calibration load successful. File: {file_name}")
            logging_repr = (
                lambda x: np.array_repr(x).replace(" ", "").replace("\n", " ")
            )
            logging.info(f"K: {logging_repr(self.K)}")
            logging.info(f"D: {logging_repr(self.D)}")
            logging.info(f"fisheye: {self.fisheye}")
            if self.frame_shape is not None:
                logging.info(f"new_K: {logging_repr(self.new_K)}")

        except Exception as e:
            self.set_cal_bad()
            logging.warning(f"Intrinsic calibration load unsuccessful. {e}")
        self.mutex.unlock()

        if self.frame_shape and self.cal_ok:
            self.intrinsic_settings_updated.emit(self.cal_ok, self.map_x, self.map_y)
        else:
            self.intrinsic_settings_updated.emit(False, None, None)

    def undistort(self, frame):
        if not self.cal_ok:
            return frame
        if self.frame_shape is None:
            self.set_frame_shape(frame.shape)
        return undistort_map(frame, self.map_x, self.map_y)

    def start_calibration_widget(self):
        calibration_widget = CalibrationWidget(self)
        calibration_widget.calibration_saved.connect(self.calibration_widget_finished)
        calibration_widget.resize(600, 400)
        calibration_widget.show()

    def calibration_widget_finished(self, path):
        self.intrinsic_cal_file_edit.blockSignals(True)
        self.intrinsic_cal_file_edit.setText(str(path))
        self.intrinsic_cal_file_edit.blockSignals(False)
        self.update_intrinsic_cal()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = LoadIntrinsicDock()
    widget.show()

    app.exec()
