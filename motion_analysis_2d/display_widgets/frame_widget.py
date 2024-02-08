import contextlib
import logging
from enum import Enum
from pathlib import Path

import cv2 as cv
import numpy as np
import pyqtgraph as pg

from motion_analysis_2d.custom_components import (
    tab10_rgb,
)
from motion_analysis_2d.defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.display_items import (
    TrackerItem,
    AngleItem,
    DistanceItem,
    SetPerspectiveItem,
)
from motion_analysis_2d.funcs import (
    setup_logger,
    is_json_file,
    check_file_type,
)


class FrameWidget(QtWidgets.QWidget):
    new_item_suggested = Signal(str, object)
    edit_item_suggested = Signal(str, str, object)
    item_moved = Signal(str, object)
    item_removal_suggested = Signal(str, str)
    marker_file_dropped = Signal(object)
    image_file_dropped = Signal(object)
    new_settings_suggested = Signal(str, object)
    new_settings_ended = Signal()

    def __init__(self, visual_settings=None, parent=None):
        super().__init__(parent=parent)

        self.setAcceptDrops(True)
        pg.setConfigOptions(
            background=None,
            foreground=self.palette().color(self.foregroundRole()),
            antialias=True,
        )
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.scaling = 1

        if visual_settings is None:
            visual_settings = {}
        self.visual_settings = {
            "new_item_pen_color": tab10_rgb["green"],
            "new_item_pen_width": 3,
            "crosshair_pen_color": tab10_rgb["cyan"],
            "crosshair_pen_width": 1,
            "trajectory_length": 30,
            "trajectory_width": 2,
            "frame_label_text_color": [255, 255, 255],
            "frame_label_fill_color": [0, 0, 0, 150],
            "instruction_label_text_color": [255, 255, 255],
            "instruction_label_fill_color": tab10_rgb["green"],
            "item_name_label_fill_color": [0, 0, 0, 150],
            "tracker_bbox_pen_width": 2,
            "tracker_bbox_hover_pen_width": 4,
            "tracker_target_size": 10,
            "tracker_target_pen_width": 2,
            "tracker_target_hover_pen_width": 4,
            "angle_sector_radius": 100,
            "angle_sector_pen_width": 1,
            "angle_sector_fill_transparency": 150,
            "angle_vector_pen_width": 1,
            "distance_arrow_stem_width": 3,
            "distance_arrow_head_width": 42,
            "distance_arrow_head_height": 42,
            "set_perspective_inner_pen_color": tab10_rgb["green"],
            "set_perspective_inner_pen_width": 2,
            "set_perspective_inner_hover_pen_color": tab10_rgb["green"],
            "set_perspective_inner_hover_pen_width": 4,
            "set_perspective_outer_pen_color": tab10_rgb["green"],
            "set_perspective_outer_pen_width": 1,
            "set_perspective_outer_hover_pen_color": tab10_rgb["green"],
            "set_perspective_outer_hover_pen_width": 3,
        }
        self.visual_settings.update(visual_settings)
        self.show_crosshairs = False
        self.mouse_mode = MouseModes.NORMAL

        self.new_item_pen = pg.mkPen(
            color=self.visual_settings["new_item_pen_color"],
            width=self.visual_settings["new_item_pen_width"],
        )
        self.crosshair_pen = pg.mkPen(
            color=self.visual_settings["crosshair_pen_color"],
            width=self.visual_settings["crosshair_pen_width"],
        )

        self.plot_widget = pg.PlotWidget()
        self.fig = self.plot_widget.getPlotItem()
        self.main_layout.addWidget(self.plot_widget)

        self.im_item = pg.ImageItem(axisOrder="row-major")
        self.fig.addItem(self.im_item)
        self.fig.setAspectLocked()
        # self.fig.invertY(True)
        self.fig.setMenuEnabled(False)
        self.fig.setLabel("left", "Pixels")
        self.fig.setLabel("bottom", "Pixels")
        self.fig.hideAxis("left")
        self.fig.hideAxis("bottom")
        self.frame_label = self.add_frame_label()
        self.instruction_label = self.add_instruction_label()
        self.crosshair_items = self.add_crosshairs()

        self.trackers = TrackerItem(self, self.new_item_pen, self.visual_settings)
        self.angles = AngleItem(
            self, self.new_item_pen, self.visual_settings, self.trackers
        )
        self.distances = DistanceItem(
            self, self.new_item_pen, self.visual_settings, self.trackers
        )
        self.display_items = {
            "tracker": self.trackers,
            "angle": self.angles,
            "distance": self.distances,
        }
        self.set_perspective_item = SetPerspectiveItem(
            self, self.new_item_pen, self.visual_settings
        )

        self.v_crosshair = pg.InfiniteLine(
            pos=pg.Point(-1000, -1000), angle=90, movable=False, pen=self.crosshair_pen
        )
        self.v_crosshair_label = pg.TextItem(
            "", anchor=(0, 1), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )
        self.h_crosshair = pg.InfiniteLine(
            pos=pg.Point(-1000, -1000), angle=0, movable=False, pen=self.crosshair_pen
        )
        self.h_crosshair_label = pg.TextItem(
            "", anchor=(0, 1), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )
        self.intensity_crosshair_label = pg.TextItem(
            "", anchor=(1, 0), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )

        self.img = None
        self.raw_img = None

        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)
        self.plot_widget.sigRangeChanged.connect(self.range_changed)

    def set_item_data(self, item_type, name, data):
        self.display_items[item_type].set_data(name, data)

    def add_item(self, item_type, item_props):
        if item_type in self.display_items:
            self.display_items[item_type].add_item(item_props)

    def edit_item_props(self, item_type, name, item_props):
        if item_type in self.display_items:
            self.display_items[item_type].edit_item_props(name, item_props)

    def remove_item(self, item_type, item_name):
        if item_type in self.display_items:
            self.display_items[item_type].remove_item(item_name)

    def start_edit_item(self, item_type, item_name):
        if item_type in self.display_items:
            self.display_items[item_type].start_edit_item(item_name)

    def hide_item(self, item_type, name, index=0):
        if item_type in self.display_items:
            self.display_items[item_type].hide_item(name, index)

    def show_item(self, item_type, name, index=0):
        if item_type in self.display_items:
            self.display_items[item_type].show_item(name, index)

    def hide_all_items(self, index=1):
        for display_item in self.display_items.values():
            for name in display_item["name"]:
                display_item.hide_item(name, index)

    def show_all_items(self, index=1):
        for display_item in self.display_items.values():
            for name in display_item["name"]:
                display_item.show_item(name, index)

    def mouse_clicked(self, evt):
        if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
            pos = evt.scenePos()
            mouse_point = self.fig.vb.mapSceneToView(pos)
            items = self.fig.scene().items(pos)
            if self.mouse_mode == MouseModes.ADD_TRACKER:
                self.trackers.mouse_clicked(mouse_point, items)
            elif self.mouse_mode == MouseModes.ADD_ANGLE:
                self.angles.mouse_clicked(mouse_point, items)
            elif self.mouse_mode == MouseModes.ADD_DISTANCE:
                self.distances.mouse_clicked(mouse_point, items)
            elif self.mouse_mode == MouseModes.REMOVE_ITEM:
                pos = evt.scenePos()
                items = self.fig.scene().items(pos)
                for display_item in self.display_items.values():
                    for item in items:
                        if display_item.remove_selected_item(item):
                            break
                    else:
                        continue
                    break

        # Double right click to toggle crosshairs
        if evt.double() and evt.button() == QtCore.Qt.RightButton:
            self.toggle_crosshairs(evt)

    def mouse_moved(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)

        if self.mouse_mode == MouseModes.ADD_TRACKER:
            self.trackers.mouse_moved(mouse_point)
        elif self.mouse_mode == MouseModes.ADD_ANGLE:
            self.angles.mouse_moved(mouse_point)
        elif self.mouse_mode == MouseModes.ADD_DISTANCE:
            self.distances.mouse_moved(mouse_point)
        self.animate_crosshairs(pos)

    def range_changed(self):
        self.adjust_crosshairs()
        self.adjust_instruction_label()
        logging.debug(f"Frame range changed.")

    def auto_range(self):
        self.fig.autoRange()
        logging.debug(f"Auto range frame.")

    def set_image(self, img, raw=False):
        if img is None:
            return
        if raw:
            self.raw_img = img
        self.img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        self.im_item.setImage(self.img)

        logging.trace(f"Set image.")

    def update_frame(self, img, frame_no, t_sec):
        self.set_image(img)
        self.update_frame_label(frame_no, t_sec)
        logging.trace(f"Frame updated.")

    def add_frame_label(self):
        frame_label = pg.TextItem(
            "Frame: {}\nTime: {:.2f} s".format(0, 0),
            anchor=(0, 0),
            color=self.visual_settings["frame_label_text_color"],
            fill=self.visual_settings["frame_label_fill_color"],
        )
        frame_label.setParentItem(self.fig.getViewBox())
        return frame_label

    def update_frame_label(self, frame_no, time, fps=None):
        if fps is None:
            self.frame_label.setText(f"Frame: {frame_no}\n" f"Time: {time:.2f} s")
        else:
            self.frame_label.setText(
                f"Frame: {frame_no}\n" f"Time: {time:.2f} s\n" f"FPS: {fps:.0f}\n"
            )
        logging.trace(f"Frame label updated: {frame_no}.")

    def update_scaling(self, scaling):
        self.scaling = scaling
        logging.debug(f"Frame scaling updated to {scaling}.")

    def add_instruction_label(self):
        frame_label = pg.TextItem(
            "",
            anchor=(0.5, 1),
            color=self.visual_settings["instruction_label_text_color"],
            fill=self.visual_settings["instruction_label_fill_color"],
        )
        view_box = self.fig.getViewBox()
        frame_label.setPos(view_box.width() / 2, view_box.height())
        # frame_label.setParentItem(view_box)
        return frame_label

    def adjust_instruction_label(self):
        view_box = self.fig.getViewBox()
        self.instruction_label.setPos(view_box.width() / 2, view_box.height())

    def show_instruction(self, text):
        self.instruction_label.setText(text)
        self.instruction_label.setParentItem(self.fig.getViewBox())
        logging.debug(f"Instruction '{text}' shown.")

    def hide_instruction(self):
        self.instruction_label.setText("")
        self.fig.getViewBox().removeItem(self.instruction_label)
        logging.debug(f"Instruction hidden.")

    def update_instructions(self, instruction=None):
        if instruction is not None:
            self.show_instruction(instruction)
        else:
            if self.instruction_label.parentItem():
                self.hide_instruction()

    def set_mouse_mode(self, mode):
        if isinstance(mode, str):
            mode = MouseModes[mode.upper()]
        if mode == MouseModes.NORMAL:
            self.plot_widget.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.plot_widget.setCursor(QtCore.Qt.CrossCursor)
        self.mouse_mode = mode

        self.trackers.reset_temp_item()
        self.angles.reset_temp_item()
        self.distances.reset_temp_item()
        self.set_perspective_item.reset_temp_item()

        if self.mouse_mode == MouseModes.ADD_TRACKER:
            self.trackers.start_item_suggestion()
        elif self.mouse_mode == MouseModes.ADD_ANGLE:
            self.angles.start_item_suggestion()
        elif self.mouse_mode == MouseModes.ADD_DISTANCE:
            self.distances.start_item_suggestion()
        elif self.mouse_mode == MouseModes.SET_PERSPECTIVE:
            self.set_perspective_item.start_item_suggestion()
        else:
            self.update_instructions()
        logging.debug(f"Mouse mode set to {mode}.")

    def frame_shape_changed(self, frame_data=None):
        if frame_data is not None:
            self.update_frame(*frame_data)
        for display_item in self.display_items.values():
            display_item.frame_shape_changed()

    def update_child_item(self, child_type, child_name, **kwargs):
        self.display_items[child_type].update_item(child_name, **kwargs)

    def update_parents_of_child(
        self, child_type, child_name, old_parent_name, new_parent_name
    ):
        self.display_items[child_type].change_parent(
            child_name, old_parent_name, new_parent_name
        )

    def clear(self):
        for items in self.display_items.values():
            items.clear()

        self.fig.clear()
        self.raw_img = None
        self.im_item = pg.ImageItem(axisOrder="row-major")
        self.fig.addItem(self.im_item)
        logging.debug(f"Frame display cleared.")

    def get_image_size(self):
        im_x, im_y = self.im_item.pos()
        im_w, im_h = self.im_item.width(), self.im_item.height()
        return im_x, im_y, im_w, im_h

    def add_crosshairs(self):
        crosshair_pen = pg.mkPen(
            color=self.visual_settings["crosshair_pen_color"],
            width=self.visual_settings["crosshair_pen_width"],
        )
        return {
            "v_crosshair": pg.InfiniteLine(
                pos=pg.Point(-1000, -1000), angle=90, movable=False, pen=crosshair_pen
            ),
            "v_crosshair_label": pg.TextItem(
                "", anchor=(0, 1), color=crosshair_pen.color(), fill=(0, 0, 0)
            ),
            "h_crosshair": pg.InfiniteLine(
                pos=pg.Point(-1000, -1000), angle=0, movable=False, pen=crosshair_pen
            ),
            "h_crosshair_label": pg.TextItem(
                "", anchor=(0, 1), color=crosshair_pen.color(), fill=(0, 0, 0)
            ),
            "intensity_crosshair_label": pg.TextItem(
                "",
                anchor=(1, 0),
                color=crosshair_pen.color(),
                fill=(0, 0, 0),
            ),
        }

    def animate_crosshairs(self, pos):
        """
        animate crosshairs and display x and y values
        """
        if not self.fig.sceneBoundingRect().contains(pos) or not self.show_crosshairs:
            return
        with contextlib.suppress(Exception):
            mouse_point = self.fig.vb.mapSceneToView(pos)
            x = round(mouse_point.x())
            y = round(mouse_point.y())
            intensity = self.img[y, x]

            self.v_crosshair.setPos(x)
            self.h_crosshair.setPos(y)

            x_real = x / self.scaling
            y_real = y / self.scaling

            xlim, ylim = self.fig.viewRange()
            self.v_crosshair_label.setText(f"{x_real:.4g}")
            self.v_crosshair_label.setPos(x, ylim[0])
            self.h_crosshair_label.setText(f"{y_real:.4g}")
            self.h_crosshair_label.setPos(xlim[0], y)
            self.intensity_crosshair_label.setText(
                "R: {}, G: {}, B: {}".format(*intensity)
            )
            self.intensity_crosshair_label.setPos(xlim[1], ylim[1])

    def toggle_crosshairs(self, evt):
        if self.show_crosshairs:
            self.show_crosshairs = False
            self.fig.removeItem(self.v_crosshair)
            self.fig.removeItem(self.v_crosshair_label)
            self.fig.removeItem(self.h_crosshair)
            self.fig.removeItem(self.h_crosshair_label)
            self.fig.removeItem(self.intensity_crosshair_label)
            logging.debug("Show crosshairs.")
        else:
            self.show_crosshairs = True
            self.fig.addItem(self.v_crosshair, ignoreBounds=True)
            self.fig.addItem(self.v_crosshair_label, ignoreBounds=True)
            self.fig.addItem(self.h_crosshair, ignoreBounds=True)
            self.fig.addItem(self.h_crosshair_label, ignoreBounds=True)
            self.fig.addItem(self.intensity_crosshair_label, ignoreBounds=True)
            self.mouse_moved(evt.scenePos())
            logging.debug("Hide crosshairs.")

    def adjust_crosshairs(self):
        """
        Move crosshair labels if resized.
        """
        if self.show_crosshairs:
            xlim, ylim = self.fig.viewRange()
            self.v_crosshair_label.setPos(self.v_crosshair_label.pos().x(), ylim[1])
            self.h_crosshair_label.setPos(xlim[0], self.h_crosshair_label.pos().y())
            self.intensity_crosshair_label.setPos(xlim[1], ylim[0])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            path = Path(e.mimeData().urls()[0].toLocalFile())
            if is_json_file(path) or check_file_type(path, ["image"]):
                e.acceptProposedAction()
                e.setDropAction(QtCore.Qt.LinkAction)
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            if is_json_file(e.mimeData().urls()[0].toLocalFile()):
                e.setDropAction(QtCore.Qt.LinkAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(QtCore.Qt.LinkAction)
            path = Path(e.mimeData().urls()[0].toLocalFile())
            if is_json_file(path):
                e.accept()

                logging.debug("Marker file dropped.")
                self.marker_file_dropped.emit(path)
            elif check_file_type(path, ["image"]):
                e.accept()

                logging.debug("Image file dropped.")
                try:
                    img = cv.imread(str(path))
                except Exception as e:
                    return
                self.set_image(img, raw=True)
                self.image_file_dropped.emit(img)
        else:
            super().dropEvent(e)


class MouseModes(Enum):
    NORMAL = 0
    ADD_TRACKER = 1
    ADD_ANGLE = 2
    ADD_DISTANCE = 3
    REMOVE_ITEM = 4
    SET_PERSPECTIVE = 5


if __name__ == "__main__":
    setup_logger(5)
    black_img = np.zeros([100, 100, 3], dtype=np.uint8)

    app = QtWidgets.QApplication([])
    widget = FrameWidget()
    widget.set_image(black_img)
    # widget.set_mouse_mode("add_tracker")
    for i, mypos in enumerate([(10, 10), (50, 50), (30, 30), (40, 20)]):
        widget.add_item(
            "tracker",
            {
                "name": f"test{i}",
                "bbox_pos": mypos,
                "bbox_size": (27, 3),
                "offset": (-2, -2),
                "color": (31, 119, 180),
                "tracker_type": "CSRT",
            },
        )
    widget.set_mouse_mode("add_angle")

    widget.show()

    app.exec()
