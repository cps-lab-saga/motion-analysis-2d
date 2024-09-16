from motion_analysis_2d.funcs import setup_logger

logger = setup_logger(__name__)


from pathlib import Path

import cv2 as cv
import numpy as np
import qtawesome as qta
from motion_analysis_2d.custom_components import BaseDock, PathEdit
from motion_analysis_2d.funcs import (
    load_extrinsic,
    save_perspective_points,
    save_only_scaling,
)
from qtpy import QtCore, QtWidgets


class LoadExtrinsicDock(BaseDock):
    extrinsic_settings_updated = QtCore.Signal(bool, object, object)
    scaling_updated = QtCore.Signal(float)
    add_perspective_started = QtCore.Signal()
    add_perspective_finished = QtCore.Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Perspective Correction and Scale")

        self.cal_ok = False
        self.transformation_matrix, self.mask, self.output_size, self.scaling = (
            None,
            None,
            None,
            1,
        )

        row = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(row)
        self.extrinsic_cal_file_edit = PathEdit("file", self)
        self.extrinsic_cal_file_edit.acceptDrops()
        self.extrinsic_cal_file_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum
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

        self.add_perspective_button = QtWidgets.QPushButton(self)
        # self.select_points_button.setText("Select Points")
        self.add_perspective_button.setToolTip("Select calibration points from frame.")
        self.add_perspective_button.setFlat(True)
        self.add_perspective_button.setCheckable(True)
        self.add_perspective_button.setIcon(qta.icon("mdi6.cursor-default-click"))
        self.add_perspective_button.toggled.connect(self.add_perspective_button_toggled)
        row.addWidget(self.add_perspective_button)

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

        self.transformation_matrix, self.mask, self.output_size, self.scaling = (
            None,
            None,
            None,
            1,
        )

    def update_extrinsic_cal(self):
        try:
            file_name = self.extrinsic_cal_file_edit.text()
            (
                self.transformation_matrix,
                self.mask,
                self.output_size,
                self.scaling,
            ) = load_extrinsic(Path(file_name).resolve())
            self.set_cal_ok()
            logger.info(f"Extrinsic calibration load successful. File: {file_name}")
            if self.transformation_matrix is not None:
                logging_repr = (
                    lambda x: np.array_repr(x).replace(" ", "").replace("\n", " ")
                )
                logger.info(f"M: {logging_repr(self.transformation_matrix)}")
                logger.info(f"output_size: {logging_repr(self.output_size)}")
            logger.info(f"scaling: {self.scaling}")

        except Exception as e:
            self.set_cal_bad()
            logger.warning(f"Extrinsic calibration load unsuccessful. {e}")

        self.extrinsic_settings_updated.emit(
            self.cal_ok, self.transformation_matrix, self.output_size
        )
        self.scaling_updated.emit(self.scaling)

    def change_perspective(self, frame):
        if self.transformation_matrix is not None:
            return (
                cv.warpPerspective(frame, self.transformation_matrix, self.output_size)
                if self.cal_ok
                else frame
            )
        else:
            return frame

    def add_perspective_button_toggled(self, checked):
        if checked:
            self.extrinsic_cal_file_edit.setText("")
            self.add_perspective_started.emit()
        else:
            self.add_perspective_finished.emit()

    def save_points(self, props):
        self.uncheck_select_points_button()
        path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save points", "perspective_points", "JSON (*.json)"
        )
        if path[1] == "JSON (*.json)":
            save_path = Path(path[0]).resolve()
            if props["mode"] == "Perspective":
                save_perspective_points(
                    props["img_points"],
                    props["obj_points"],
                    props["output_size"],
                    save_path,
                )
            elif props["mode"] == "Scaling":
                save_only_scaling(
                    props["img_points"],
                    props["real_distance"],
                    save_path,
                )
            else:
                logger.critical("Invalid extrinsic data!")

            self.extrinsic_cal_file_edit.setText(str(save_path.resolve()))

    def uncheck_select_points_button(self):
        self.add_perspective_button.blockSignals(True)
        self.add_perspective_button.setChecked(False)
        self.add_perspective_button.blockSignals(False)

    def gui_save(self, settings):
        self.uncheck_select_points_button()
        super().gui_save(settings)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = LoadExtrinsicDock()
    widget.show()

    app.exec()
