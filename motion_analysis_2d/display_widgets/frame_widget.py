import contextlib
import logging
from enum import Enum
from pathlib import Path

import cv2 as cv
import numpy as np
import pyqtgraph as pg

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import PieItem, ArrowItem, tab10_rgb
from motion_analysis_2d.dialogs import PointDialog
from motion_analysis_2d.funcs import (
    setup_logger,
    is_json_file,
    angle_vec,
)


class FrameWidget(QtWidgets.QWidget):
    new_tracker_suggested = Signal(tuple, tuple, tuple)
    tracker_moved = Signal(str, tuple, tuple, tuple, tuple, str)
    tracker_removal_suggested = Signal(str)
    new_angle_suggested = Signal(str, str, str, str)
    angle_moved = Signal(str, str, str, str, str, tuple)
    angle_removal_suggested = Signal(str)
    new_distance_suggested = Signal(str, str)
    distance_moved = Signal(str, str, str, tuple)
    distance_removal_suggested = Signal(str)
    marker_file_dropped = Signal(object)
    new_warp_points_selected = Signal(list, list)

    def __init__(self, visual_settings=None, parent=None):
        super().__init__(parent=parent)

        if visual_settings is None:
            visual_settings = {}

        self.setAcceptDrops(True)

        pg.setConfigOptions(
            background=None,
            foreground=self.palette().color(self.foregroundRole()),
            antialias=True,
        )

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.scaling = 1

        self.show_crosshairs = False
        self.mouse_mode = MouseModes.NORMAL
        self.add_tracker_steps = (
            "Select first point for tracking box.",
            "Select second point for tracking box.",
            "Select target point.",
        )
        self.tracker_steps_index = 0
        self.add_angle_steps = (
            "Select tracker for start point of first vector.",
            "Select tracker for end point of first vector.",
            "Select tracker for start point of second vector.",
            "Select tracker for end point of second vector.",
        )
        self.angle_steps_index = 0
        self.add_distance_steps = (
            "Select first tracker to measure distance.",
            "Select second tracker to measure distance.",
        )
        self.distance_steps_index = 0
        self.remove_tracker_instructions = "Select tracker to remove."
        self.remove_angle_instructions = "Select angle to remove."
        self.remove_distance_instructions = "Select distance to remove."

        self.select_warp_points_instructions = (
            "Add calibration points to warp perspective: "
        )
        self.warp_points_steps_index = 0

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
            "warp_point_symbol": "d",
            "warp_point_color": tab10_rgb["blue"],
        }
        self.visual_settings.update(visual_settings)

        self.new_item_pen = pg.mkPen(
            color=self.visual_settings["new_item_pen_color"],
            width=self.visual_settings["new_item_pen_width"],
        )
        self.crosshair_pen = pg.mkPen(
            color=self.visual_settings["crosshair_pen_color"],
            width=self.visual_settings["crosshair_pen_width"],
        )
        self.warp_point_brush = pg.mkBrush(
            color=self.visual_settings["warp_point_color"]
        )

        self.trackers = {
            "name": [],
            "roi": [],
            "label": [],
            "target": [],
            "traj": [],
            "offset": [],
            "color": [],
            "tracker_type": [],
            "children": [],
            "show": [],
        }
        self.angles = {
            "name": [],
            "vec1": [],
            "vec2": [],
            "pie": [],
            "label": [],
            "start1": [],
            "end1": [],
            "start2": [],
            "end2": [],
            "color": [],
            "show": [],
        }
        self.distances = {
            "name": [],
            "arrow": [],
            "label": [],
            "start": [],
            "end": [],
            "color": [],
            "show": [],
        }

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
        self.temp_tracker = None
        self.temp_angle = None
        self.temp_distance = None
        self.temp_warp_points = None

        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)
        self.plot_widget.sigRangeChanged.connect(self.range_changed)

    def mouse_clicked(self, evt):
        if self.mouse_mode == MouseModes.ADD_TRACKER:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                if self.tracker_steps_index == 0:
                    self.start_new_tracker(evt.scenePos())
                elif self.tracker_steps_index == 1:
                    self.finish_new_tracker(evt.scenePos())
                elif self.tracker_steps_index == 2:
                    self.select_tracker_target(evt.scenePos())

        elif self.mouse_mode == MouseModes.REMOVE_TRACKER:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                pos = evt.scenePos()
                items = self.fig.scene().items(pos)
                for item in items:
                    if isinstance(item, (pg.ROI, pg.TargetItem)):
                        self.remove_tracker_suggested(item)
                        break

        elif self.mouse_mode == MouseModes.ADD_ANGLE:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                if self.angle_steps_index == 0:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.start_new_angle(item)
                            break
                elif self.angle_steps_index == 1:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.select_angle_tracker_end1(item)
                            break
                elif self.angle_steps_index == 2:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.select_angle_tracker_start2(item)
                            break
                elif self.angle_steps_index == 3:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.select_angle_tracker_end2(item)
                            break

        elif self.mouse_mode == MouseModes.REMOVE_ANGLE:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                pos = evt.scenePos()
                items = self.fig.scene().items(pos)
                for item in items:
                    if isinstance(item, PieItem):
                        self.remove_angle_suggested(item)
                        break
                    elif isinstance(item, pg.PlotCurveItem):
                        if item in self.angles["vec1"] or item in self.angles["vec2"]:
                            self.remove_angle_suggested(item)
                            break

        elif self.mouse_mode == MouseModes.ADD_DISTANCE:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                if self.distance_steps_index == 0:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.start_new_distance(item)
                            break
                elif self.distance_steps_index == 1:
                    pos = evt.scenePos()
                    items = self.fig.scene().items(pos)
                    for item in items:
                        if isinstance(item, pg.TargetItem):
                            self.select_distance_tracker_end(item)
                            break

        elif self.mouse_mode == MouseModes.REMOVE_DISTANCE:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                pos = evt.scenePos()
                items = self.fig.scene().items(pos)
                for item in items:
                    if isinstance(item, ArrowItem):
                        self.remove_distance_suggested(item)
                        break

        elif self.mouse_mode == MouseModes.SELECT_WARP_POINTS:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                if self.warp_points_steps_index == 0:
                    self.start_new_warp_points(evt.scenePos())
                else:
                    self.add_warp_point(evt.scenePos())

        self.update_instructions()

        # Double right click to toggle crosshairs
        if evt.double() and evt.button() == QtCore.Qt.RightButton:
            self.toggle_crosshairs(evt)

    def mouse_moved(self, pos):
        if self.mouse_mode == MouseModes.ADD_TRACKER:
            if self.tracker_steps_index == 1:
                self.shape_new_tracker(pos)
        elif self.mouse_mode == MouseModes.ADD_ANGLE:
            if self.angle_steps_index == 1:
                self.shape_new_angle(pos, 1)
            elif self.angle_steps_index == 3:
                self.shape_new_angle(pos, 2)
        elif self.mouse_mode == MouseModes.ADD_DISTANCE:
            if self.distance_steps_index == 1:
                self.shape_new_distance(pos)

        self.animate_crosshairs(pos)

    def range_changed(self):
        self.adjust_crosshairs()
        self.adjust_instruction_label()
        logging.trace(f"Frame range changed.")

    def auto_range(self):
        self.fig.autoRange()
        logging.debug(f"Auto range frame.")

    def set_image(self, img):
        if img is None:
            return

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
        logging.debug(f"Instruction {text} shown.")

    def hide_instruction(self):
        self.instruction_label.setText("")
        self.fig.getViewBox().removeItem(self.instruction_label)
        logging.debug(f"Instruction hidden.")

    def update_instructions(self):
        if self.mouse_mode == MouseModes.ADD_TRACKER:
            self.show_instruction(self.add_tracker_steps[self.tracker_steps_index])
        elif self.mouse_mode == MouseModes.REMOVE_TRACKER:
            self.show_instruction(self.remove_tracker_instructions)
        elif self.mouse_mode == MouseModes.ADD_ANGLE:
            self.show_instruction(self.add_angle_steps[self.angle_steps_index])
        elif self.mouse_mode == MouseModes.REMOVE_ANGLE:
            self.show_instruction(self.remove_angle_instructions)
        elif self.mouse_mode == MouseModes.ADD_DISTANCE:
            self.show_instruction(self.add_distance_steps[self.distance_steps_index])
        elif self.mouse_mode == MouseModes.REMOVE_DISTANCE:
            self.show_instruction(self.remove_distance_instructions)
        elif self.mouse_mode == MouseModes.SELECT_WARP_POINTS:
            self.show_instruction(
                self.select_warp_points_instructions + f"{self.warp_points_steps_index}"
            )
        else:
            self.hide_instruction()

    def set_mouse_mode(self, mode):
        if isinstance(mode, str):
            mode = MouseModes[mode.upper()]
        if mode == MouseModes.NORMAL:
            self.plot_widget.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.plot_widget.setCursor(QtCore.Qt.CrossCursor)
        self.mouse_mode = mode

        logging.debug(f"Mouse mode set to {mode}.")

        # Reset steps
        self.tracker_steps_index = 0
        self.angle_steps_index = 0
        self.distance_steps_index = 0
        self.warp_points_steps_index = 0

        self.update_instructions()

    def start_new_tracker(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        x, y = self.keep_point_in_frame(x, y)
        new_roi = pg.ROI(
            (x, y),
            size=(0, 0),
            pen=self.new_item_pen,
            movable=False,
            resizable=False,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )

        # default (centre of bounding box)
        target_x, target_y = [round(a) for a in self.calc_centre_roi(new_roi)]
        target = pg.TargetItem(
            (target_x, target_y),
            size=self.visual_settings["tracker_target_size"],
            pen=pg.mkPen(None),
            brush=pg.mkBrush(None),
            movable=False,
        )

        self.temp_tracker = {"roi": new_roi, "target": target}
        self.fig.addItem(self.temp_tracker["roi"])
        self.fig.addItem(self.temp_tracker["target"])

        logging.debug(f"New tracker bbox started at {mouse_point}.")

        self.next_add_tracker_step()

    def shape_new_tracker(self, pos):
        roi_x, roi_y = self.temp_tracker["roi"].pos()
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x, y = self.keep_point_in_frame(mouse_point.x(), mouse_point.y())

        w = round(x) - roi_x
        h = round(y) - roi_y
        self.temp_tracker["roi"].setSize((w, h))

        # default (centre of bounding box)
        target_x, target_y = [
            round(a) for a in self.calc_centre_roi(self.temp_tracker["roi"])
        ]
        self.temp_tracker["target"].setPos((target_x, target_y))
        return mouse_point

    def finish_new_tracker(self, pos):
        mouse_point = self.shape_new_tracker(pos)

        x, y = self.temp_tracker["roi"].pos()
        w, h = self.temp_tracker["roi"].size()

        # make roi size positive (origin at bottom left)
        if w < 0:
            x = round(x + w)
            w = round(abs(w))
        if h < 0:
            y = round(y + h)
            h = round(abs(h))
        self.temp_tracker["roi"].setPos((x, y))
        self.temp_tracker["roi"].setSize((w, h))

        # default (centre of bounding box)
        target_x, target_y = [
            round(a) for a in self.calc_centre_roi(self.temp_tracker["roi"])
        ]
        self.temp_tracker["target"].setPos((target_x, target_y))

        logging.debug(f"New tracker bbox completed at {mouse_point}.")

        self.next_add_tracker_step()

    def select_tracker_target(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        self.temp_tracker["target"].setPos((x, y))
        self.temp_tracker["target"].setPen(self.new_item_pen)

        logging.debug(f"New tracker target selected at {mouse_point}.")

        self.next_add_tracker_step()

    def next_add_tracker_step(self):
        if self.tracker_steps_index >= len(self.add_tracker_steps) - 1:
            self.emit_new_tracker_suggestion()
            self.tracker_steps_index = 0
        else:
            self.tracker_steps_index += 1

    def emit_new_tracker_suggestion(self):
        if self.temp_tracker is None:
            return

        x, y = (round(a) for a in self.temp_tracker["roi"].pos())
        w, h = (round(a) for a in self.temp_tracker["roi"].size())

        offset_x, offset_y = [
            round(a)
            for a in (
                self.temp_tracker["target"].pos()
                - self.calc_centre_roi(self.temp_tracker["roi"])
            )
        ]  # from centre of roi

        logging.debug(
            f"Drawn tracker with bbox_pos {(x, y)}, bbox_size {(w, h)}, offset {(offset_x, offset_y)}."
        )

        self.new_tracker_suggested.emit(
            (x, y),
            (w, h),
            (offset_x, offset_y),
        )

    @staticmethod
    def calc_centre_roi(roi):
        return roi.pos() + roi.size() / 2

    def remove_temp_tracker(self):
        if self.temp_tracker is not None:
            self.fig.removeItem(self.temp_tracker["roi"])
            self.fig.removeItem(self.temp_tracker["target"])
            self.temp_tracker = None
            logging.debug("Removed incomplete tracker from frame.")

    def remove_temp_angle(self):
        if self.temp_angle is not None:
            self.fig.removeItem(self.temp_angle["vec1"])
            self.fig.removeItem(self.temp_angle["vec2"])
            self.temp_angle = None
            logging.debug("Removed incomplete angle from frame.")

    def remove_temp_distance(self):
        if self.temp_distance is not None:
            self.fig.removeItem(self.temp_distance["arrow"])
            self.temp_distance = None
            logging.debug("Removed incomplete distance from frame.")

    def remove_warp_points(self):
        if self.temp_warp_points is not None:
            self.fig.removeItem(self.temp_warp_points["plot_points"])
            self.temp_warp_points = None
            logging.debug("Removed drawn warp points from frame.")

    def add_tracker(self, name, bbox_pos, bbox_size, offset, color, tracker_type):
        bbox_pen = pg.mkPen(
            color=color, width=self.visual_settings["tracker_bbox_pen_width"]
        )
        bbox_hover_pen = pg.mkPen(
            color=color, width=self.visual_settings["tracker_bbox_hover_pen_width"]
        )
        target_pen = pg.mkPen(
            color=color, width=self.visual_settings["tracker_target_pen_width"]
        )
        target_hover_pen = pg.mkPen(
            color=color, width=self.visual_settings["tracker_bbox_hover_pen_width"]
        )
        trajectory_pen = pg.mkPen(
            color=color, width=self.visual_settings["trajectory_width"]
        )

        roi = pg.ROI(
            bbox_pos,
            size=bbox_size,
            pen=bbox_pen,
            hoverPen=bbox_hover_pen,
            movable=True,
            resizable=True,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )
        roi.addScaleHandle([0, 1], [0.5, 0.5])
        roi.sigRegionChanged.connect(self.bbox_moved)
        roi.setZValue(0)
        self.fig.addItem(roi)

        cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
        target_pos = cx + offset[0], cy + offset[1]
        target = pg.TargetItem(
            target_pos,
            size=self.visual_settings["tracker_target_size"],
            pen=target_pen,
            hoverPen=target_hover_pen,
            movable=True,
        )
        target.sigPositionChanged.connect(self.target_moved)
        target.setZValue(1)
        self.fig.addItem(target)

        label = pg.TargetLabel(
            target,
            name,
            offset=(-20, 0),
            anchor=(0, 1),
            color=target_pen.color(),
            fill=self.visual_settings["item_name_label_fill_color"],
        )

        traj = self.fig.plot(pen=trajectory_pen)

        self.trackers["name"].append(name)
        self.trackers["roi"].append(roi)
        self.trackers["target"].append(target)
        self.trackers["label"].append(label)
        self.trackers["traj"].append(traj)
        self.trackers["offset"].append(offset)
        self.trackers["color"].append(color)
        self.trackers["tracker_type"].append(tracker_type)
        self.trackers["children"].append(set())
        self.trackers["show"].append(True)

        logging.debug(f"Tracker {name} added to frame display.")

    def edit_tracker(self, name, new_name, new_color, new_tracker_type):
        i = self.trackers["name"].index(name)
        self.trackers["name"][i] = new_name
        self.trackers["color"][i] = new_color
        self.trackers["tracker_type"][i] = new_tracker_type

        bbox_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["tracker_bbox_pen_width"]
        )
        bbox_hover_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["tracker_bbox_hover_pen_width"]
        )
        self.trackers["roi"][i].setPen(bbox_pen)
        self.trackers["roi"][i].hoverPen = bbox_hover_pen

        target_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["tracker_target_pen_width"]
        )
        target_hover_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["tracker_bbox_hover_pen_width"]
        )
        self.trackers["target"][i].setPen(target_pen)
        self.trackers["target"][i].setHoverPen(target_hover_pen)
        self.trackers["label"][i].setColor(target_pen.color())
        self.trackers["label"][i].setText(new_name)

        trajectory_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["trajectory_width"]
        )
        self.trackers["traj"][i].setPen(trajectory_pen)

        if new_name != name:
            children = self.trackers["children"][i]
            if len(children) > 0:
                for child_name, child_type in children:
                    if child_type == "angle":
                        self.update_angle_parent_name(child_name, name, new_name)
                    elif child_type == "distance":
                        self.update_distance_parent_name(child_name, name, new_name)

    def hide_tracker(self, name):
        i = self.trackers["name"].index(name)
        if not self.trackers["show"][i]:
            return
        else:
            self.fig.removeItem(self.trackers["roi"][i])
            self.fig.removeItem(self.trackers["target"][i])
            self.fig.removeItem(self.trackers["traj"][i])
            self.trackers["show"][i] = False
            logging.debug(f"Tracker {name} hidden in frame display.")

    def show_tracker(self, name):
        i = self.trackers["name"].index(name)
        if self.trackers["show"][i]:
            return
        else:
            self.fig.addItem(self.trackers["roi"][i])
            self.fig.addItem(self.trackers["target"][i])
            self.fig.addItem(self.trackers["traj"][i])
            self.trackers["show"][i] = True
            logging.debug(f"Tracker {name} shown in frame display.")

    def remove_tracker_suggested(self, item):
        if isinstance(item, pg.ROI):
            i = self.trackers["roi"].index(item)
        elif isinstance(item, pg.TargetItem):
            i = self.trackers["target"].index(item)
        else:
            raise TypeError("Unrecognized item type")
        name = self.trackers["name"][i]
        self.tracker_removal_suggested.emit(name)

    def remove_tracker(self, name):
        i = self.trackers["name"].index(name)

        children = self.trackers["children"][i]
        if self.trackers["show"][i]:
            self.fig.removeItem(self.trackers["roi"][i])
            self.fig.removeItem(self.trackers["target"][i])
            self.fig.removeItem(self.trackers["traj"][i])

        if len(children) > 0:
            all_children = children.copy()
            for child_name, child_type in all_children:
                if child_type == "angle":
                    self.angle_removal_suggested.emit(child_name)
                elif child_type == "distance":
                    self.distance_removal_suggested.emit(child_name)

        for item in self.trackers.values():
            item.pop(i)

        logging.debug(f"Tracker {name} removed from frame display.")

    def frame_shape_changed(self, frame_data=None):
        if frame_data is not None:
            self.update_frame(*frame_data)
        for roi in self.trackers["roi"]:
            self.bbox_moved(roi)

    def bbox_moved(self, roi=None):
        if roi is None:
            roi = self.sender()
        roi_x, roi_y, roi_w, roi_h = self.keep_roi_in_frame(roi)

        i = self.trackers["roi"].index(roi)
        name = self.trackers["name"][i]
        target = self.trackers["target"][i]
        offset = self.trackers["offset"][i]
        bbox_pos = [round(a) for a in (roi_x, roi_y)]
        bbox_size = [round(a) for a in (roi_w, roi_h)]
        tracker_type = self.trackers["tracker_type"][i]
        color = self.trackers["color"][i]
        children = self.trackers["children"][i]

        cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
        target_pos = cx + offset[0], cy + offset[1]

        target.blockSignals(True)
        target.setPos(target_pos)
        if len(children) > 0:
            for child_name, child_type in children:
                if child_type == "angle":
                    self.update_angle_item(child_name, dragged=True)
                elif child_type == "distance":
                    self.update_distance_item(child_name, dragged=True)
        target.blockSignals(False)

        logging.debug(f"Tracker {name} roi moved in frame display.")
        self.tracker_moved.emit(name, bbox_pos, bbox_size, offset, color, tracker_type)

    def target_moved(self):
        target = self.sender()

        i = self.trackers["target"].index(target)
        name = self.trackers["name"][i]
        roi = self.trackers["roi"][i]
        bbox_pos = [round(a) for a in roi.pos()]
        bbox_size = [round(a) for a in roi.size()]
        offset = [round(a) for a in target.pos() - self.calc_centre_roi(roi)]
        tracker_type = self.trackers["tracker_type"][i]
        color = self.trackers["color"][i]
        children = self.trackers["children"][i]
        self.trackers["offset"][i] = offset

        if len(children) > 0:
            for child_name, child_type in children:
                if child_type == "angle":
                    self.update_angle_item(child_name, dragged=True)
                elif child_type == "distance":
                    self.update_distance_item(child_name, dragged=True)

        logging.debug(f"Tracker {name} target moved in frame display.")
        self.tracker_moved.emit(name, bbox_pos, bbox_size, offset, color, tracker_type)

    def start_new_angle(self, target_item):
        x, y = target_item.pos()
        i = self.trackers["target"].index(target_item)
        start_name = self.trackers["name"][i]

        vec1 = self.fig.plot([x], [y], pen=self.new_item_pen)
        vec2 = self.fig.plot(pen=self.new_item_pen)

        self.temp_angle = {
            "vec1": vec1,
            "vec2": vec2,
            "start1": start_name,
            "end1": None,
            "start2": None,
            "end2": None,
        }

        logging.debug(f"New angle 1st vector started at Tracker {start_name}.")
        self.next_add_angle_step()

    def select_angle_tracker_end(self, target_item, vec_no):
        i = self.trackers["target"].index(target_item)
        name = self.trackers["name"][i]
        self.temp_angle[f"end{vec_no}"] = name

        start_name = self.temp_angle[f"start{vec_no}"]
        start_x, start_y = self.get_target_pos_from_tracker_name(start_name)

        end_name = self.temp_angle[f"end{vec_no}"]
        end_x, end_y = self.get_target_pos_from_tracker_name(end_name)

        self.temp_angle[f"vec{vec_no}"].setData([start_x, end_x], [start_y, end_y])
        return end_name

    def select_angle_tracker_end1(self, target_item):
        end_name = self.select_angle_tracker_end(target_item, 1)
        logging.debug(f"New angle 1st vector ended at Tracker {end_name}.")
        self.next_add_angle_step()

    def select_angle_tracker_start2(self, target_item):
        i = self.trackers["target"].index(target_item)
        name = self.trackers["name"][i]
        self.temp_angle[f"start2"] = name

        logging.debug(f"New angle 2nd vector started at Tracker {name}.")
        self.next_add_angle_step()

    def select_angle_tracker_end2(self, target_item):
        end_name = self.select_angle_tracker_end(target_item, 2)

        logging.debug(f"New angle 2nd vector ended at Tracker {end_name}.")
        self.next_add_angle_step()

    def shape_new_angle(self, pos, vec_no):
        start_name = self.temp_angle[f"start{vec_no}"]
        vec = self.temp_angle[f"vec{vec_no}"]

        start_x, start_y = self.get_target_pos_from_tracker_name(start_name)

        mouse_point = self.fig.vb.mapSceneToView(pos)
        vec.setData([start_x, mouse_point.x()], [start_y, mouse_point.y()])

    def get_target_pos_from_tracker_name(self, name):
        i = self.trackers["name"].index(name)
        return self.trackers["target"][i].pos()

    def add_children_to_tracker(self, tracker_name, child_name, child_type):
        i = self.trackers["name"].index(tracker_name)
        if (child_name, child_type) not in self.trackers["children"][i]:
            self.trackers["children"][i].add((child_name, child_type))
        logging.debug(
            f"Child {(child_name, child_type)} added to Tracker {tracker_name}."
        )

    def remove_children_from_tracker(self, tracker_name, child_name, child_type):
        i = self.trackers["name"].index(tracker_name)
        self.trackers["children"][i].discard((child_name, child_type))
        logging.debug(
            f"Child {(child_name, child_type)} removed from Tracker {tracker_name}."
        )

    def next_add_angle_step(self):
        if self.angle_steps_index >= len(self.add_angle_steps) - 1:
            self.emit_new_angler_suggestion()
            self.angle_steps_index = 0
        else:
            self.angle_steps_index += 1

    def emit_new_angler_suggestion(self):
        if self.temp_angle is None:
            return

        logging.debug(
            f"Drawn angle with 1st vector from {self.temp_angle['start1']} to {self.temp_angle['end1']}, "
            f"2nd vector from {self.temp_angle['start2']} to {self.temp_angle['end2']}."
        )
        self.new_angle_suggested.emit(
            self.temp_angle["start1"],
            self.temp_angle["end1"],
            self.temp_angle["start2"],
            self.temp_angle["end2"],
        )

    def add_angle(self, name, start1, end1, start2, end2, color):
        sector_pen = pg.mkPen(
            color=color, width=self.visual_settings["angle_sector_pen_width"]
        )
        sector_brush = pg.mkBrush(
            color=(
                *sector_pen.color().toTuple()[:3],
                self.visual_settings["angle_sector_fill_transparency"],
            )
        )
        vector_pen = pg.mkPen(
            color=color, width=self.visual_settings["angle_vector_pen_width"]
        )

        for n in [start1, end1, start2, end2]:
            self.add_children_to_tracker(n, name, "angle")

        vec1_start_x, vec1_start_y = self.get_target_pos_from_tracker_name(start1)
        vec1_end_x, vec1_end_y = self.get_target_pos_from_tracker_name(end1)
        vec2_start_x, vec2_start_y = self.get_target_pos_from_tracker_name(start2)
        vec2_end_x, vec2_end_y = self.get_target_pos_from_tracker_name(end2)

        vec1 = pg.PlotCurveItem(
            [vec1_start_x, vec1_end_x],
            [vec1_start_y, vec1_end_y],
            pen=vector_pen,
        )
        self.fig.addItem(vec1)
        vec2 = pg.PlotCurveItem(
            [vec2_start_x, vec2_end_x],
            [vec2_start_y, vec2_end_y],
            pen=vector_pen,
        )
        self.fig.addItem(vec2)
        (vec1_angle,) = angle_vec(
            [[vec1_end_x - vec1_start_x, vec1_end_y - vec1_start_y]]
        )
        (vec2_angle,) = angle_vec(
            [[vec2_end_x - vec2_start_x, vec2_end_y - vec2_start_y]]
        )

        pie = PieItem(
            center=(vec1_start_x, vec1_start_y),
            radius=self.visual_settings["angle_sector_radius"],
            start_angle=vec1_angle,
            span_angle=vec2_angle - vec1_angle,
            pen=sector_pen,
            brush=sector_brush,
        )
        self.fig.addItem(pie)

        label = pg.TextItem(
            name,
            anchor=(0, 0.5),
            color=sector_pen.color(),
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        label.setPos(
            round(vec1_start_x) + self.visual_settings["angle_sector_radius"],
            round(vec1_start_y),
        )
        self.fig.addItem(label)

        self.angles["name"].append(name)
        self.angles["vec1"].append(vec1)
        self.angles["vec2"].append(vec2)
        self.angles["pie"].append(pie)
        self.angles["label"].append(label)
        self.angles["start1"].append(start1)
        self.angles["end1"].append(end1)
        self.angles["start2"].append(start2)
        self.angles["end2"].append(end2)
        self.angles["color"].append(color)
        self.angles["show"].append(True)

        logging.debug(f"Angle {name} added to frame display.")

    def edit_angle(self, name, new_name, new_color):
        i = self.angles["name"].index(name)
        self.angles["name"][i] = new_name
        self.angles["color"][i] = new_color

        sector_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["angle_sector_pen_width"]
        )
        sector_brush = pg.mkBrush(
            color=(
                *sector_pen.color().toTuple()[:3],
                self.visual_settings["angle_sector_fill_transparency"],
            )
        )
        vector_pen = pg.mkPen(
            color=new_color, width=self.visual_settings["angle_vector_pen_width"]
        )

        self.angles["vec1"][i].setPen(vector_pen)
        self.angles["vec2"][i].setPen(vector_pen)
        self.angles["pie"][i].setPen(sector_pen)
        self.angles["pie"][i].setBrush(sector_brush)

        self.angles["label"][i].setColor(sector_pen.color())
        self.angles["label"][i].setText(new_name)

        if new_name != name:
            for children in self.trackers["children"]:
                if (name, "angle") in children:
                    children.remove((name, "angle"))
                    children.add((new_name, "angle"))

    def update_angle_parent_name(self, name, parent_name, new_parent_name):
        i = self.angles["name"].index(name)
        for x in ["start1", "end1", "start2", "end2"]:
            if self.angles[x][i] == parent_name:
                self.angles[x][i] = new_parent_name

    def update_angle_item(self, name, dragged=False):
        i = self.angles["name"].index(name)
        start1 = self.angles["start1"][i]
        end1 = self.angles["end1"][i]
        start2 = self.angles["start2"][i]
        end2 = self.angles["end2"][i]
        color = self.angles["color"][i]
        vec1 = self.angles["vec1"][i]
        vec2 = self.angles["vec2"][i]
        pie = self.angles["pie"][i]
        label = self.angles["label"][i]

        vec1_start_x, vec1_start_y = self.get_target_pos_from_tracker_name(start1)
        vec1_end_x, vec1_end_y = self.get_target_pos_from_tracker_name(end1)
        vec2_start_x, vec2_start_y = self.get_target_pos_from_tracker_name(start2)
        vec2_end_x, vec2_end_y = self.get_target_pos_from_tracker_name(end2)

        (vec1_angle,) = angle_vec(
            [[vec1_end_x - vec1_start_x, vec1_end_y - vec1_start_y]]
        )
        (vec2_angle,) = angle_vec(
            [[vec2_end_x - vec2_start_x, vec2_end_y - vec2_start_y]]
        )

        vec1.setData(
            [vec1_start_x, vec1_end_x],
            [vec1_start_y, vec1_end_y],
        )
        vec2.setData(
            [vec2_start_x, vec2_end_x],
            [vec2_start_y, vec2_end_y],
        )

        pie.setData(
            center=(vec1_start_x, vec1_start_y),
            radius=self.visual_settings["angle_sector_radius"],
            start_angle=vec1_angle,
            span_angle=vec2_angle - vec1_angle,
        )
        label.setPos(
            round(vec1_start_x) + self.visual_settings["angle_sector_radius"],
            round(vec1_start_y),
        )

        if dragged:
            logging.debug(f"Angle {name} manually moved in frame display.")
            self.angle_moved.emit(name, start1, end1, start2, end2, color)

    def hide_angle(self, name):
        i = self.angles["name"].index(name)
        if not self.angles["show"][i]:
            return
        else:
            self.fig.removeItem(self.angles["vec1"][i])
            self.fig.removeItem(self.angles["vec2"][i])
            self.fig.removeItem(self.angles["pie"][i])
            self.fig.removeItem(self.angles["label"][i])
            self.angles["show"][i] = False
            logging.debug(f"Angle {name} hidden in frame display.")

    def show_angle(self, name):
        i = self.angles["name"].index(name)
        if self.angles["show"][i]:
            return
        else:
            self.fig.addItem(self.angles["vec1"][i])
            self.fig.addItem(self.angles["vec2"][i])
            self.fig.addItem(self.angles["pie"][i])
            self.fig.addItem(self.angles["label"][i])
            self.angles["show"][i] = True
            logging.debug(f"Angle {name} shown in frame display.")

    def remove_angle_suggested(self, item):
        if isinstance(item, PieItem):
            i = self.angles["pie"].index(item)
        elif isinstance(item, pg.PlotCurveItem):
            if item in self.angles["vec1"]:
                i = self.angles["vec1"].index(item)
            elif item in self.angles["vec2"]:
                i = self.angles["vec2"].index(item)
            else:
                return
        else:
            raise TypeError("Unrecognized item type")
        name = self.angles["name"][i]
        self.angle_removal_suggested.emit(name)

    def remove_angle(self, name):
        i = self.angles["name"].index(name)

        start1 = self.angles["start1"][i]
        end1 = self.angles["end1"][i]
        start2 = self.angles["start2"][i]
        end2 = self.angles["end2"][i]
        if self.angles["show"][i]:
            self.fig.removeItem(self.angles["vec1"][i])
            self.fig.removeItem(self.angles["vec2"][i])
            self.fig.removeItem(self.angles["pie"][i])
            self.fig.removeItem(self.angles["label"][i])

        for n in [start1, end1, start2, end2]:
            self.remove_children_from_tracker(n, name, "angle")

        for item in self.angles.values():
            item.pop(i)

        logging.debug(f"Angle {name} removed from frame display.")

    def start_new_distance(self, target_item):
        x, y = target_item.pos()
        i = self.trackers["target"].index(target_item)
        start_name = self.trackers["name"][i]

        arrow = ArrowItem(
            start_pos=(x, y),
            end_pos=(x, y),
            arrow_width=self.visual_settings["distance_arrow_head_width"],
            arrow_height=self.visual_settings["distance_arrow_head_height"],
            stem_pen=self.new_item_pen,
            arrow_pen=pg.mkPen(None),
            arrow_brush=pg.mkBrush(color=self.new_item_pen.color()),
        )
        self.fig.addItem(arrow)

        self.temp_distance = {
            "arrow": arrow,
            "start": start_name,
            "end": None,
        }

        logging.debug(f"New distance started at Tracker {start_name}.")
        self.next_add_distance_step()

    def select_distance_tracker_end(self, target_item):
        i = self.trackers["target"].index(target_item)
        name = self.trackers["name"][i]
        self.temp_distance[f"end"] = name

        start_name = self.temp_distance[f"start"]
        start_pos = self.get_target_pos_from_tracker_name(start_name)

        end_name = self.temp_distance[f"end"]
        end_pos = self.get_target_pos_from_tracker_name(end_name)

        self.temp_distance[f"arrow"].setData(start_pos, end_pos)

        logging.debug(f"New distance ended at Tracker {end_name}.")
        self.next_add_distance_step()

    def shape_new_distance(self, pos):
        start_name = self.temp_distance[f"start"]
        arrow = self.temp_distance[f"arrow"]

        start_pos = self.get_target_pos_from_tracker_name(start_name)

        mouse_point = self.fig.vb.mapSceneToView(pos)
        arrow.setData(start_pos.toTuple(), mouse_point.toTuple())
        self.fig.update()

    def next_add_distance_step(self):
        if self.distance_steps_index >= len(self.add_distance_steps) - 1:
            self.emit_new_distance_suggestion()
            self.distance_steps_index = 0
        else:
            self.distance_steps_index += 1

    def emit_new_distance_suggestion(self):
        if self.temp_distance is None:
            return

        logging.debug(
            f"Drawn distance from {self.temp_distance['start']} to {self.temp_distance['end']}."
        )
        self.new_distance_suggested.emit(
            self.temp_distance["start"],
            self.temp_distance["end"],
        )

    def add_distance(self, name, start, end, color):
        pen = pg.mkPen(
            color=color, width=self.visual_settings["distance_arrow_stem_width"]
        )
        brush = pg.mkBrush(color=color)

        for n in [start, end]:
            self.add_children_to_tracker(n, name, "distance")

        start_pos = self.get_target_pos_from_tracker_name(start)
        end_pos = self.get_target_pos_from_tracker_name(end)

        arrow = ArrowItem(
            start_pos=start_pos,
            end_pos=end_pos,
            arrow_width=self.visual_settings["distance_arrow_head_width"],
            arrow_height=self.visual_settings["distance_arrow_head_height"],
            stem_pen=pen,
            arrow_pen=pg.mkPen(None),
            arrow_brush=brush,
        )
        self.fig.addItem(arrow)

        label = pg.TextItem(
            name,
            anchor=(0, 0.5),
            color=pen.color(),
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        label.setPos((start_pos + end_pos) / 2)
        self.fig.addItem(label)

        self.distances["name"].append(name)
        self.distances["arrow"].append(arrow)
        self.distances["label"].append(label)
        self.distances["start"].append(start)
        self.distances["end"].append(end)
        self.distances["color"].append(color)
        self.distances["show"].append(True)

        logging.debug(f"Distance {name} added to frame display.")

    def edit_distance(self, name, new_name, new_color):
        i = self.distances["name"].index(name)
        self.distances["name"][i] = new_name
        self.distances["color"][i] = new_color

        pen = pg.mkPen(
            color=new_color, width=self.visual_settings["distance_arrow_stem_width"]
        )
        brush = pg.mkBrush(color=new_color)

        self.distances["arrow"][i].setStemPen(pen)
        self.distances["arrow"][i].setArrowPen(pen)
        self.distances["arrow"][i].setArrowBrush(brush)

        self.distances["label"][i].setColor(pen.color())
        self.distances["label"][i].setText(new_name)

        if new_name != name:
            for children in self.trackers["children"]:
                if (name, "distance") in children:
                    children.remove((name, "distance"))
                    children.add((new_name, "distance"))

    def update_distance_parent_name(self, name, parent_name, new_parent_name):
        i = self.distances["name"].index(name)
        for x in ["start", "end"]:
            if self.distances[x][i] == parent_name:
                self.distances[x][i] = new_parent_name

    def update_distance_item(self, name, dragged=False):
        i = self.distances["name"].index(name)
        start = self.distances["start"][i]
        end = self.distances["end"][i]
        arrow = self.distances["arrow"][i]
        label = self.distances["label"][i]
        color = self.distances["color"][i]

        start_pos = self.get_target_pos_from_tracker_name(start)
        end_pos = self.get_target_pos_from_tracker_name(end)

        arrow.setData(start_pos, end_pos)
        label.setPos((start_pos + end_pos) / 2)

        if dragged:
            logging.debug(f"Distance {name} manually moved in frame display.")
            self.distance_moved.emit(name, start, end, color)

    def hide_distance(self, name):
        i = self.distances["name"].index(name)
        if not self.distances["show"][i]:
            return
        else:
            self.fig.removeItem(self.distances["arrow"][i])
            self.fig.removeItem(self.distances["label"][i])
            self.distances["show"][i] = False
            logging.debug(f"Distance {name} hidden in frame display.")

    def show_distance(self, name):
        i = self.distances["name"].index(name)
        if self.distances["show"][i]:
            return
        else:
            self.fig.addItem(self.distances["arrow"][i])
            self.fig.addItem(self.distances["label"][i])
            self.distances["show"][i] = True
            logging.debug(f"Distance {name} shown in frame display.")

    def remove_distance_suggested(self, item):
        if isinstance(item, ArrowItem):
            i = self.distances["arrow"].index(item)
        else:
            raise TypeError("Unrecognized item type")
        name = self.distances["name"][i]
        self.distance_removal_suggested.emit(name)

    def remove_distance(self, name):
        i = self.distances["name"].index(name)

        start = self.distances["start"][i]
        end = self.distances["end"][i]
        self.fig.removeItem(self.distances["arrow"][i])
        self.fig.removeItem(self.distances["label"][i])

        for n in [start, end]:
            self.remove_children_from_tracker(n, name, "distance")

        for item in self.distances.values():
            item.pop(i)

        logging.debug(f"Distance {name} removed from frame display.")

    def clear(self):
        for l in self.trackers.values():
            l.clear()
        for l in self.angles.values():
            l.clear()
        for l in self.distances.values():
            l.clear()

        self.fig.clear()
        self.im_item = pg.ImageItem(axisOrder="row-major")
        self.fig.addItem(self.im_item)
        logging.debug(f"Frame display cleared.")

    def keep_roi_in_frame(self, roi):
        roi_x, roi_y = roi.pos()
        roi_w, roi_h = roi.size()
        im_x, im_y = self.im_item.pos()
        im_w, im_h = self.im_item.width(), self.im_item.height()

        if roi_w >= im_w:
            roi_w = im_w
        if roi_h >= im_h:
            roi_h = im_h
        if roi_w < 2:
            roi_w = 2
        if roi_h < 2:
            roi_h = 2
        if roi_w / roi_h > 20:
            roi_h = roi_w / 20
        elif roi_h / roi_w > 20:
            roi_w = roi_h / 20

        if roi_x < im_x:
            roi_x = im_x
        if roi_x + roi_w > im_x + im_w:
            roi_x = im_x + im_w - roi_w
        if roi_y < im_y:
            roi_y = im_y
        if roi_y + roi_h > im_y + im_h:
            roi_y = im_y + im_h - roi_h

        roi.blockSignals(True)
        roi.setPos((roi_x, roi_y))
        roi.setSize((roi_w, roi_h))
        roi.blockSignals(False)

        return roi_x, roi_y, roi_w, roi_h

    def keep_point_in_frame(self, x, y):
        im_x, im_y = self.im_item.pos()
        im_w, im_h = self.im_item.width(), self.im_item.height()

        if x > im_x + im_w:
            x = im_x + im_w
        elif x < im_x:
            x = im_x
        if y > im_y + im_h:
            y = im_y + im_h
        elif y < im_y:
            y = im_y

        return x, y

    def move_tracker(self, name, bbox, target_pos):
        i = self.trackers["name"].index(name)
        roi = self.trackers["roi"][i]
        target = self.trackers["target"][i]
        offset = self.trackers["offset"][i]
        children = self.trackers["children"][i]

        if np.isnan(bbox).any() or np.isnan(target_pos).any():
            roi.blockSignals(True)
            target.blockSignals(True)
            roi.setPos(
                (
                    self.im_item.pos()[0] + self.im_item.width(),
                    i * roi.size()[1] * 2,
                )
            )
            target.setPos((roi.pos()[0] + offset[0], roi.pos()[1] + offset[1]))
            roi.blockSignals(False)
            target.blockSignals(False)
            logging.trace(f"Tracker move pos are not available.")
        else:
            bbox_pos = bbox[:2]
            bbox_size = bbox[2:]
            roi.blockSignals(True)
            roi.setPos(bbox_pos)
            roi.setSize(bbox_size)
            roi.blockSignals(False)

            target.blockSignals(True)
            target.setPos(target_pos)
            target.blockSignals(False)

            self.trackers["offset"][i] = [
                round(a) for a in target.pos() - self.calc_centre_roi(roi)
            ]
            logging.trace(f"Tracker {name} moved.")

        if len(children) > 0:
            for child_name, child_type in children:
                if child_type == "angle":
                    self.update_angle_item(child_name)
                elif child_type == "distance":
                    self.update_distance_item(child_name)

    def show_trajectory(self, name, current_frame_index, target):
        i = self.trackers["name"].index(name)
        traj = self.trackers["traj"][i]
        if current_frame_index > self.visual_settings["trajectory_length"]:
            traj.setData(
                target[
                    current_frame_index
                    - self.visual_settings["trajectory_length"] : current_frame_index,
                    0,
                ],
                target[
                    current_frame_index
                    - self.visual_settings["trajectory_length"] : current_frame_index,
                    1,
                ],
            )
        else:
            traj.setData(
                target[:current_frame_index, 0], target[:current_frame_index, 1]
            )
        logging.trace(f"Tracker trajectory updated.")

    def start_new_warp_points(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        x, y = self.keep_point_in_frame(x, y)

        img_point = (x, y)
        plot_points = self.fig.plot(
            np.array([img_point]),
            pen=pg.mkPen(None),
            symbolBrush=self.warp_point_brush,
            symbol=self.visual_settings["warp_point_symbol"],
        )
        dialog = PointDialog(img_point, "Point 1")
        dialog.exec()
        if dialog.result():
            obj_points, finish = dialog.get_result()
            self.temp_warp_points = {
                "plot_points": plot_points,
                "img_points": [img_point],
                "obj_points": [obj_points],
            }
            logging.debug(
                f"Perspective warp point started at {img_point}, labeled as {obj_points}."
            )
            self.next_warp_point_step()
            if finish:
                self.emit_new_warp_points()
        else:
            self.fig.removeItem(plot_points)

    def add_warp_point(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        x, y = self.keep_point_in_frame(x, y)

        img_point = (x, y)
        self.temp_warp_points["plot_points"].setData(
            np.array(self.temp_warp_points["img_points"] + [img_point])
        )

        dialog = PointDialog(
            img_point, f"Point {len(self.temp_warp_points['img_points']) + 1}"
        )
        dialog.exec()
        if dialog.result():
            obj_points, finish = dialog.get_result()
            self.temp_warp_points["img_points"].append((x, y))
            self.temp_warp_points["obj_points"].append(obj_points)
            logging.debug(
                f"Perspective warp point added at {img_point}, labeled as {obj_points}."
            )
            self.next_warp_point_step()
            if finish:
                self.emit_new_warp_points()
        else:
            self.temp_warp_points["plot_points"].setData(
                np.array(self.temp_warp_points["img_points"])
            )

    def next_warp_point_step(self):
        self.warp_points_steps_index += 1

    def emit_new_warp_points(self):
        if self.temp_warp_points is None:
            return

        self.warp_points_steps_index = 0
        img_points = self.temp_warp_points["img_points"]
        obj_points = self.temp_warp_points["obj_points"]
        self.fig.removeItem(self.temp_warp_points["plot_points"])

        self.temp_warp_points = None
        self.set_mouse_mode(MouseModes.NORMAL)
        logging.debug(
            f"Drawn and labeled point finished with {img_points}, {obj_points}."
        )
        self.new_warp_points_selected.emit(img_points, obj_points)

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
            if is_json_file(e.mimeData().urls()[0].toLocalFile()):
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
        else:
            super().dropEvent(e)


class MouseModes(Enum):
    NORMAL = 0
    ADD_TRACKER = 1
    REMOVE_TRACKER = 2
    ADD_ANGLE = 3
    REMOVE_ANGLE = 4
    ADD_DISTANCE = 5
    REMOVE_DISTANCE = 6
    SELECT_WARP_POINTS = 7


if __name__ == "__main__":
    setup_logger(5)
    black_img = np.zeros([100, 100, 3], dtype=np.uint8)

    app = QtWidgets.QApplication([])
    widget = FrameWidget()
    widget.set_image(black_img)
    # widget.set_mouse_mode("add_tracker")

    widget.add_tracker("test1", (20, 40), (5, 5), (0, 0), "green", "")
    widget.add_tracker("test2", (40, 40), (5, 5), (0, 0), "green", "")
    widget.add_tracker("test3", (20, 40), (5, 5), (0, 0), "green", "")
    widget.add_tracker("test4", (40, 40), (5, 5), (0, 0), "green", "")

    widget.set_mouse_mode("add_angle")
    widget.add_angle("angle1", "test1", "test2", "test3", "test4", "green")

    # widget.set_mouse_mode("add_distance")
    # widget.add_distance("distance1", "test1", "test2", "green")

    # widget.set_mouse_mode("select_warp_points")

    widget.show()

    app.exec()
