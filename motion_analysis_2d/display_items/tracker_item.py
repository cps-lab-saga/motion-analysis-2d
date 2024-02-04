import logging
from functools import partial

import numpy as np
import pyqtgraph as pg

from motion_analysis_2d.custom_components import tab10_rgb_cycle
from motion_analysis_2d.dialogs import TrackerDialog
from .base_item_display import BaseDisplayItem


class TrackerItem(BaseDisplayItem):
    def __init__(self, display, new_item_pen, visual_settings):
        super().__init__(display, new_item_pen, visual_settings)

        self.dragging_mode = "bbox_follows_target"
        self.item_type_name = "tracker"

        self._items = {
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
        self.temp_item = None
        self.display_item_types = (pg.ROI, pg.TargetItem)
        self.display_item_names = ("roi", "target", "traj")
        self.steps = (
            "Starting...",
            "Select target point.",
            "Select first point for tracking box.",
            "Select second point for tracking box.",
            "Set name and properties.",
        )
        self.steps_index = 0

    def start_item_suggestion(self):
        new_roi = pg.ROI(
            (0, 0),
            size=(0, 0),
            pen=pg.mkPen(None),
            movable=False,
            resizable=False,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )
        target = pg.TargetItem(
            (0, 0),
            size=self.visual_settings["tracker_target_size"],
            pen=pg.mkPen(None),
            brush=pg.mkBrush(None),
            movable=False,
        )
        self.temp_item = {"roi": new_roi, "target": target}
        self.add_items_to_display([self.temp_item["roi"], self.temp_item["target"]])

        self.steps_index = 1
        self.update_instructions()

    def reset_temp_item(self):
        if self.temp_item is not None:
            self.remove_items_from_display(
                [self.temp_item["roi"], self.temp_item["target"]]
            )
            self.temp_item = None
            self.steps_index = 0
            self.update_instructions()

    def mouse_clicked(self, mouse_point, items):
        if self.steps_index == 1:
            self.set_target(mouse_point)
        elif self.steps_index == 2:
            self.set_first_bbox_point(mouse_point)
        elif self.steps_index == 3:
            self.set_second_bbox_point(mouse_point)

    def mouse_moved(self, mouse_point):
        if self.steps_index == 3:
            self.shape_new_tracker(mouse_point)

    def set_target(self, mouse_point):
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        self.temp_item["target"].setPos((x, y))
        self.temp_item["target"].setPen(self.new_item_pen)
        self.steps_index = 2
        self.update_instructions()

    def set_first_bbox_point(self, mouse_point):
        self.temp_item["roi"].setPen(self.new_item_pen)

        x = round(mouse_point.x())
        y = round(mouse_point.y())
        x, y = self.keep_point_in_frame(x, y)
        self.temp_item["roi"].setPos((x, y))
        self.steps_index = 3
        self.update_instructions()

    def set_second_bbox_point(self, mouse_point):
        self.shape_new_tracker(mouse_point)

        # make roi size positive (origin at bottom left)
        x, y = self.temp_item["roi"].pos()
        w, h = self.temp_item["roi"].size()
        if w < 0:
            x = round(x + w)
            w = round(abs(w))
        if h < 0:
            y = round(y + h)
            h = round(abs(h))
        self.temp_item["roi"].setPos((x, y))
        self.temp_item["roi"].setSize((w, h))

        self.finish_temp_item()

    def finish_temp_item(self):
        if self.temp_item is None:
            return

        x, y = (round(a) for a in self.temp_item["roi"].pos())
        w, h = (round(a) for a in self.temp_item["roi"].size())

        offset_x, offset_y = [
            round(a)
            for a in (
                self.temp_item["target"].pos()
                - self.calc_centre_roi(self.temp_item["roi"])
            )
        ]  # from centre of roi

        props = {
            "bbox_pos": (x, y),
            "bbox_size": (w, h),
            "offset": (offset_x, offset_y),
        }

        self.steps_index = 4
        self.update_instructions()
        self.set_additional_props(props)

    def set_additional_props(self, props):
        dialog = TrackerDialog(default_color=next(tab10_rgb_cycle))
        dialog.exec()
        if dialog.result():
            name, color, tracker_type = dialog.get_inputs()
            name = self.prevent_name_collision(name)
            props.update({"name": name, "color": color, "tracker_type": tracker_type})
            self.emit_new_item(props)
        else:
            self.start_item_suggestion()
        self.reset_temp_item()

    def shape_new_tracker(self, mouse_point):
        roi_x, roi_y = self.temp_item["roi"].pos()
        x, y = self.keep_point_in_frame(mouse_point.x(), mouse_point.y())

        w = round(x) - roi_x
        h = round(y) - roi_y
        self.temp_item["roi"].setSize((w, h))

    def add_item(self, props):
        bbox_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["tracker_bbox_pen_width"]
        )
        bbox_hover_pen = pg.mkPen(
            color=props["color"],
            width=self.visual_settings["tracker_bbox_hover_pen_width"],
        )
        target_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["tracker_target_pen_width"]
        )
        target_hover_pen = pg.mkPen(
            color=props["color"],
            width=self.visual_settings["tracker_bbox_hover_pen_width"],
        )
        trajectory_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["trajectory_width"]
        )

        roi = pg.ROI(
            props["bbox_pos"],
            size=props["bbox_size"],
            pen=bbox_pen,
            hoverPen=bbox_hover_pen,
            movable=True,
            resizable=True,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )
        roi.addScaleHandle([0, 1], [0.5, 0.5])
        roi.sigRegionChanged.connect(partial(self.bbox_moved, props["name"]))
        roi.setZValue(0)

        cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
        target_pos = cx + props["offset"][0], cy + props["offset"][1]
        target = pg.TargetItem(
            target_pos,
            size=self.visual_settings["tracker_target_size"],
            pen=target_pen,
            hoverPen=target_hover_pen,
            movable=True,
        )
        target.sigPositionChanged.connect(partial(self.target_moved, props["name"]))
        target.setZValue(1)

        label = pg.TargetLabel(
            target,
            props["name"],
            offset=(-20, 0),
            anchor=(0, 1),
            color=target_pen.color(),
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        traj = pg.PlotDataItem(pen=trajectory_pen)
        self.add_items_to_display([target, roi, traj])

        self._items["name"].append(props["name"])
        self._items["roi"].append(roi)
        self._items["target"].append(target)
        self._items["label"].append(label)
        self._items["traj"].append(traj)
        self._items["offset"].append(props["offset"])
        self._items["color"].append(props["color"])
        self._items["tracker_type"].append(props["tracker_type"])
        self._items["children"].append(set())
        self._items["show"].append([True, True, True])

        logging.debug(f"Tracker {props['name']} added to frame display.")

    def edit_item_props(self, name, props):
        i = self._items["name"].index(name)
        self._items["name"][i] = props["name"]
        self._items["color"][i] = props["color"]
        self._items["tracker_type"][i] = props["tracker_type"]

        bbox_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["tracker_bbox_pen_width"]
        )
        bbox_hover_pen = pg.mkPen(
            color=props["color"],
            width=self.visual_settings["tracker_bbox_hover_pen_width"],
        )
        self._items["roi"][i].setPen(bbox_pen)
        self._items["roi"][i].hoverPen = bbox_hover_pen

        target_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["tracker_target_pen_width"]
        )
        target_hover_pen = pg.mkPen(
            color=props["color"],
            width=self.visual_settings["tracker_bbox_hover_pen_width"],
        )
        self._items["target"][i].setPen(target_pen)
        self._items["target"][i].setHoverPen(target_hover_pen)
        self._items["label"][i].setColor(target_pen.color())
        self._items["label"][i].setText(props["name"])

        trajectory_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["trajectory_width"]
        )
        self._items["traj"][i].setPen(trajectory_pen)

        if props["name"] != name:
            children = self._items["children"][i]
            if len(children) > 0:
                for child_name, child_type in children:
                    self.update_parents_of_child(
                        child_type, child_name, name, props["name"]
                    )

    def frame_shape_changed(self):
        for name in self._items["name"]:
            self.bbox_moved(name)

    def bbox_moved(self, name, roi=None):
        i = self._items["name"].index(name)
        roi = self._items["roi"][i]
        target = self._items["target"][i]
        offset = self._items["offset"][i]
        tracker_type = self._items["tracker_type"][i]
        color = self._items["color"][i]
        children = self._items["children"][i]

        roi_x, roi_y, roi_w, roi_h = self.keep_roi_in_frame(roi)
        bbox_pos = [round(a) for a in (roi_x, roi_y)]
        bbox_size = [round(a) for a in (roi_w, roi_h)]

        if self.dragging_mode == "target_follows_bbox":
            cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
            target_pos = cx + offset[0], cy + offset[1]

            target.blockSignals(True)
            target.setPos(target_pos)
            target.blockSignals(False)

        elif self.dragging_mode == "bbox_follows_target":
            offset = [round(a) for a in target.pos() - self.calc_centre_roi(roi)]
            self._items["offset"][i] = offset
        else:
            raise Exception("Unknown dragging mode")

        if len(children) > 0:
            for child_name, child_type in children:
                self.update_child_item(child_type, child_name, dragged=True)

        props = {
            "name": name,
            "bbox_pos": bbox_pos,
            "bbox_size": bbox_size,
            "offset": offset,
            "color": color,
            "tracker_type": tracker_type,
        }

        self.item_moved("tracker", props)

    def target_moved(self, name, target=None):
        i = self._items["name"].index(name)
        target = self._items["target"][i]
        offset = self._items["offset"][i]
        roi = self._items["roi"][i]
        tracker_type = self._items["tracker_type"][i]
        color = self._items["color"][i]
        children = self._items["children"][i]

        if self.dragging_mode == "target_follows_bbox":
            bbox_pos = [round(a) for a in roi.pos()]
            bbox_size = [round(a) for a in roi.size()]
            offset = [round(a) for a in target.pos() - self.calc_centre_roi(roi)]
            self._items["offset"][i] = offset
        elif self.dragging_mode == "bbox_follows_target":
            roi.blockSignals(True)
            roi.setPos(
                *[
                    round(t - o - s / 2)
                    for t, o, s in zip(target.pos(), offset, roi.size())
                ]
            )
            roi_x, roi_y, roi_w, roi_h = self.keep_roi_in_frame(roi)
            bbox_pos = [round(a) for a in (roi_x, roi_y)]
            bbox_size = [round(a) for a in (roi_w, roi_h)]
            roi.blockSignals(False)
        else:
            raise Exception("Unknown dragging mode")

        if len(children) > 0:
            for child_name, child_type in children:
                self.update_child_item(child_type, child_name, dragged=True)

        props = {
            "name": name,
            "bbox_pos": bbox_pos,
            "bbox_size": bbox_size,
            "offset": offset,
            "color": color,
            "tracker_type": tracker_type,
        }
        self.item_moved("tracker", props)

    def set_data(self, name, data):
        frame_i, bbox_all, target_all = data
        self.set_tracker_pos(name, frame_i, bbox_all, target_all)
        self.set_trajectory(name, frame_i, bbox_all, target_all)

    def set_tracker_pos(self, name, frame_i, bbox_all, target_all):
        i = self._items["name"].index(name)
        roi = self._items["roi"][i]
        target = self._items["target"][i]
        offset = self._items["offset"][i]
        children = self._items["children"][i]

        bbox_i = bbox_all[frame_i]
        target_i = target_all[frame_i]

        if np.isnan(bbox_i).any() or np.isnan(target_i).any():
            im_x, im_y, im_w, im_h = self.get_image_size()
            roi.blockSignals(True)
            target.blockSignals(True)
            roi.setPos(
                (
                    im_x + im_w,
                    i * roi.size()[1] * 2,
                )
            )
            target.setPos((roi.pos()[0] + offset[0], roi.pos()[1] + offset[1]))
            roi.blockSignals(False)
            target.blockSignals(False)
            logging.trace(f"Tracker move pos are not available.")
        else:
            bbox_pos = bbox_i[:2]
            bbox_size = bbox_i[2:]
            roi.blockSignals(True)
            roi.setPos(bbox_pos)
            roi.setSize(bbox_size)
            roi.blockSignals(False)

            target.blockSignals(True)
            target.setPos(target_i)
            target.blockSignals(False)

            self._items["offset"][i] = [
                round(a) for a in target.pos() - self.calc_centre_roi(roi)
            ]
            logging.trace(f"Tracker {name} moved.")

        if len(children) > 0:
            for child_name, child_type in children:
                self.update_child_item(child_type, child_name, dragged=False)

    def set_trajectory(self, name, frame_i, bbox_all, target_all):
        i = self._items["name"].index(name)
        traj = self._items["traj"][i]
        if frame_i > self.visual_settings["trajectory_length"]:
            traj.setData(
                target_all[
                    frame_i - self.visual_settings["trajectory_length"] : frame_i,
                    0,
                ],
                target_all[
                    frame_i - self.visual_settings["trajectory_length"] : frame_i,
                    1,
                ],
            )
        else:
            traj.setData(target_all[:frame_i, 0], target_all[:frame_i, 1])

    def start_edit_item(self, name):
        i = self._items["name"].index(name)
        color = self._items["color"][i]
        tracker_type = self._items["tracker_type"][i]

        dialog = TrackerDialog(
            default_name=name, default_color=color, default_tracker_type=tracker_type
        )
        dialog.exec()
        if dialog.result():
            new_name, new_color, new_tracker_type = dialog.get_inputs()
            if new_name != name:
                new_name = self.prevent_name_collision(new_name)
            props = {
                "name": new_name,
                "color": new_color,
                "tracker_type": new_tracker_type,
            }
            self.emit_edit_item(name, props)

    @staticmethod
    def calc_centre_roi(roi):
        return roi.pos() + roi.size() / 2

    def keep_point_in_frame(self, x, y):
        im_x, im_y, im_w, im_h = self.get_image_size()

        if x > im_x + im_w:
            x = im_x + im_w
        elif x < im_x:
            x = im_x
        if y > im_y + im_h:
            y = im_y + im_h
        elif y < im_y:
            y = im_y

        return x, y

    def keep_roi_in_frame(self, roi):
        roi_x, roi_y = roi.pos()
        roi_w, roi_h = roi.size()
        im_x, im_y, im_w, im_h = self.get_image_size()

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
