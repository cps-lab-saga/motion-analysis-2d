import logging

import pyqtgraph as pg

from motion_analysis_2d.custom_components import tab10_rgb_cycle, PieItem
from motion_analysis_2d.dialogs import AngleDialog
from motion_analysis_2d.funcs import angle_vec
from .base_item_display import BaseDisplayItem


class AngleItem(BaseDisplayItem):
    def __init__(self, display, new_item_pen, visual_settings, parent):
        super().__init__(display, new_item_pen, visual_settings, parent)

        self.item_type_name = "angle"
        self._items = {
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
        self.temp_item = None
        self.display_item_types = (pg.PlotCurveItem, PieItem)
        self.display_item_names = ("vec1", "vec2", "pie", "label")
        self.parent_item_names = ("start1", "end1", "start2", "end2")

        self.steps = (
            "Starting...",
            "Select tracker for start point of first vector.",
            "Select tracker for end point of first vector.",
            "Select tracker for start point of second vector.",
            "Select tracker for end point of second vector.",
            "Set name and properties.",
        )
        self.steps_index = 0

    def start_item_suggestion(self):
        vec1 = pg.PlotDataItem(pen=pg.mkPen(None))
        vec2 = pg.PlotDataItem(pen=pg.mkPen(None))

        self.temp_item = {
            "vec1": vec1,
            "vec2": vec2,
            "start1": None,
            "end1": None,
            "start2": None,
            "end2": None,
        }
        self.add_items_to_display([self.temp_item["vec1"], self.temp_item["vec2"]])

        self.steps_index = 1
        self.update_instructions()

    def reset_temp_item(self):
        if self.temp_item is not None:
            self.remove_items_from_display(
                [self.temp_item["vec1"], self.temp_item["vec2"]]
            )
            self.temp_item = None
            self.steps_index = 0
            self.update_instructions()

    def mouse_clicked(self, mouse_point, items):
        if self.steps_index == 1:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_start1(item)
                    break
        elif self.steps_index == 2:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_end1(item)
                    break
        elif self.steps_index == 3:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_start2(item)
                    break
        elif self.steps_index == 4:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_end2(item)
                    break

    def mouse_moved(self, mouse_point):
        if self.steps_index == 2:
            self.shape_new_angle(mouse_point, 1)
        elif self.steps_index == 4:
            self.shape_new_angle(mouse_point, 2)

    def set_start1(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["start1"] = self.parent["name"][i]
        self.temp_item["vec1"].setPen(self.new_item_pen)

        self.steps_index = 2
        self.update_instructions()

    def set_end1(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["end1"] = self.parent["name"][i]

        start_name = self.temp_item["start1"]
        start_x, start_y = self.get_pos_from_parent_name(start_name)

        end_name = self.temp_item["end1"]
        end_x, end_y = self.get_pos_from_parent_name(end_name)

        self.temp_item[f"vec1"].setData([start_x, end_x], [start_y, end_y])
        self.steps_index = 3
        self.update_instructions()

    def set_start2(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["start2"] = self.parent["name"][i]
        self.temp_item["vec2"].setPen(self.new_item_pen)

        self.steps_index = 4
        self.update_instructions()

    def set_end2(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["end2"] = self.parent["name"][i]

        start_name = self.temp_item["start2"]
        start_x, start_y = self.get_pos_from_parent_name(start_name)

        end_name = self.temp_item["end2"]
        end_x, end_y = self.get_pos_from_parent_name(end_name)

        self.temp_item[f"vec2"].setData([start_x, end_x], [start_y, end_y])

        self.finish_temp_item()

    def finish_temp_item(self):
        if self.temp_item is None:
            return

        props = {
            "start1": self.temp_item["start1"],
            "end1": self.temp_item["end1"],
            "start2": self.temp_item["start2"],
            "end2": self.temp_item["end2"],
        }

        self.steps_index = 5
        self.update_instructions()
        self.set_additional_props(props)

    def set_additional_props(self, props):
        dialog = AngleDialog(default_color=next(tab10_rgb_cycle))
        dialog.exec()
        if dialog.result():
            name, color = dialog.get_inputs()
            name = self.prevent_name_collision(name)
            props.update({"name": name, "color": color})
            self.emit_new_item(props)
            self.reset_temp_item()
        else:
            self.reset_temp_item()
            self.start_item_suggestion()

    def shape_new_angle(self, mouse_point, vec_no):
        start_name = self.temp_item[f"start{vec_no}"]
        vec = self.temp_item[f"vec{vec_no}"]
        start_x, start_y = self.get_pos_from_parent_name(start_name)
        vec.setData([start_x, mouse_point.x()], [start_y, mouse_point.y()])

    def add_item(self, props):
        sector_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["angle_sector_pen_width"]
        )
        sector_brush = pg.mkBrush(
            color=(
                *sector_pen.color().toTuple()[:3],
                self.visual_settings["angle_sector_fill_transparency"],
            )
        )
        vector_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["angle_vector_pen_width"]
        )

        for n in self.parent_item_names:
            self.add_child_to_parent(props[n], props["name"])

        vec1_start_x, vec1_start_y = self.get_pos_from_parent_name(props["start1"])
        vec1_end_x, vec1_end_y = self.get_pos_from_parent_name(props["end1"])
        vec2_start_x, vec2_start_y = self.get_pos_from_parent_name(props["start2"])
        vec2_end_x, vec2_end_y = self.get_pos_from_parent_name(props["end2"])
        (vec1_angle,) = angle_vec(
            [[vec1_end_x - vec1_start_x, vec1_end_y - vec1_start_y]]
        )
        (vec2_angle,) = angle_vec(
            [[vec2_end_x - vec2_start_x, vec2_end_y - vec2_start_y]]
        )

        vec1 = pg.PlotCurveItem(
            [vec1_start_x, vec1_end_x],
            [vec1_start_y, vec1_end_y],
            pen=vector_pen,
        )
        vec2 = pg.PlotCurveItem(
            [vec2_start_x, vec2_end_x],
            [vec2_start_y, vec2_end_y],
            pen=vector_pen,
        )
        pie = PieItem(
            center=(vec1_start_x, vec1_start_y),
            radius=self.visual_settings["angle_sector_radius"],
            start_angle=vec1_angle,
            span_angle=vec2_angle - vec1_angle,
            pen=sector_pen,
            brush=sector_brush,
        )
        label = pg.TextItem(
            props["name"],
            anchor=(0, 0.5),
            color=sector_pen.color(),
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        self.add_items_to_display([vec1, vec2, pie, label])

        self._items["name"].append(props["name"])
        self._items["vec1"].append(vec1)
        self._items["vec2"].append(vec2)
        self._items["pie"].append(pie)
        self._items["label"].append(label)
        self._items["start1"].append(props["start1"])
        self._items["end1"].append(props["end1"])
        self._items["start2"].append(props["start2"])
        self._items["end2"].append(props["end2"])
        self._items["color"].append(props["color"])
        self._items["show"].append([True, True, True])

        logging.debug(f"Angle {props['name']} added to frame display.")

    def edit_item_props(self, name, props):
        i = self._items["name"].index(name)
        self._items["name"][i] = props["name"]
        self._items["color"][i] = props["color"]

        sector_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["angle_sector_pen_width"]
        )
        sector_brush = pg.mkBrush(
            color=(
                *sector_pen.color().toTuple()[:3],
                self.visual_settings["angle_sector_fill_transparency"],
            )
        )
        vector_pen = pg.mkPen(
            color=props["color"], width=self.visual_settings["angle_vector_pen_width"]
        )
        self._items["vec1"][i].setPen(vector_pen)
        self._items["vec2"][i].setPen(vector_pen)
        self._items["pie"][i].setPen(sector_pen)
        self._items["pie"][i].setBrush(sector_brush)
        self._items["label"][i].setColor(sector_pen.color())
        self._items["label"][i].setText(props["name"])

        if props["name"] != name:
            for children in self.parent["children"]:
                if (name, "angle") in children:
                    children.remove((name, "angle"))
                    children.add((props["name"], "angle"))

    def update_item(self, name, dragged=False):
        i = self._items["name"].index(name)
        start1 = self._items["start1"][i]
        end1 = self._items["end1"][i]
        start2 = self._items["start2"][i]
        end2 = self._items["end2"][i]
        color = self._items["color"][i]
        vec1 = self._items["vec1"][i]
        vec2 = self._items["vec2"][i]
        pie = self._items["pie"][i]
        label = self._items["label"][i]

        vec1_start_x, vec1_start_y = self.get_pos_from_parent_name(start1)
        vec1_end_x, vec1_end_y = self.get_pos_from_parent_name(end1)
        vec2_start_x, vec2_start_y = self.get_pos_from_parent_name(start2)
        vec2_end_x, vec2_end_y = self.get_pos_from_parent_name(end2)

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
        props = {
            "name": name,
            "start1": start1,
            "end1": end1,
            "start2": start2,
            "end2": end2,
        }
        if dragged:
            self.item_moved("angle", props)

    def start_edit_item(self, name):
        i = self._items["name"].index(name)
        color = self._items["color"][i]

        dialog = AngleDialog(default_name=name, default_color=color)
        dialog.exec()
        if dialog.result():
            new_name, new_color = dialog.get_inputs()
            if new_name != name:
                new_name = self.prevent_name_collision(new_name)
            props = {
                "name": new_name,
                "color": new_color,
            }
            self.emit_edit_item(name, props)

    def get_pos_from_parent_name(self, name):
        i = self.parent["name"].index(name)
        return self.parent["target"][i].pos()
