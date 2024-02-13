import logging

import pyqtgraph as pg

from motion_analysis_2d.custom_components import tab10_rgb_cycle, ArrowItem
from motion_analysis_2d.dialogs import DistanceDialog
from .base_item_display import BaseDisplayItem


class DistanceItem(BaseDisplayItem):
    def __init__(self, display, new_item_pen, visual_preferences, parent):
        super().__init__(display, new_item_pen, visual_preferences, parent)

        self.item_type_name = "distance"
        self._items = {
            "name": [],
            "arrow": [],
            "label": [],
            "start": [],
            "end": [],
            "color": [],
            "show": [],
        }
        self.temp_item = None
        self.display_item_types = [ArrowItem]
        self.display_item_names = ("arrow", "label")
        self.parent_item_names = ("start", "end")

        self.steps = (
            "Starting...",
            "Select tracker for start point.",
            "Select tracker for end point.",
            "Set name and properties.",
        )
        self.steps_index = 0

    def update_visual_preferences(self, preferences, new_item_pen):
        super().update_visual_preferences(preferences, new_item_pen)
        for i in range(len(self._items["name"])):
            color = self._items["color"][i]
            arrow = self._items["arrow"][i]
            label = self._items["label"][i]

            pen = pg.mkPen(
                color=color,
                width=self.visual_preferences["distance_arrow_stem_width"],
            )
            brush = pg.mkBrush(color=color)

            arrow.setStemPen(pen)
            arrow.setArrowBrush(brush)
            arrow.setArrowSize(
                self.visual_preferences["distance_arrow_head_width"],
                self.visual_preferences["distance_arrow_head_height"],
            )

            label.fill = pg.mkBrush(
                self.visual_preferences["item_name_label_fill_color"]
            )

    def start_item_suggestion(self):
        arrow = ArrowItem(
            start_pos=(0, 0),
            end_pos=(0, 0),
            arrow_width=self.visual_preferences["distance_arrow_head_width"],
            arrow_height=self.visual_preferences["distance_arrow_head_height"],
            stem_pen=self.new_item_pen,
            arrow_pen=pg.mkPen(None),
            arrow_brush=pg.mkBrush(None),
        )

        self.temp_item = {
            "arrow": arrow,
            "start": None,
            "end": None,
        }
        self.add_items_to_display([self.temp_item["arrow"]])

        self.steps_index = 1
        self.update_instructions()

    def reset_temp_item(self):
        if self.temp_item is not None:
            self.remove_items_from_display([self.temp_item["arrow"]])
            self.temp_item = None
            self.steps_index = 0
            self.update_instructions()

    def mouse_clicked(self, mouse_point, items):
        if self.steps_index == 1:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_start(item)
                    break
        elif self.steps_index == 2:
            for item in items:
                if isinstance(item, pg.TargetItem):
                    self.set_end(item)
                    break

    def mouse_moved(self, mouse_point):
        if self.steps_index == 2:
            self.shape_new_distance(mouse_point)

    def set_start(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["start"] = self.parent["name"][i]
        self.temp_item["arrow"].setArrowBrush(
            pg.mkBrush(color=self.new_item_pen.color())
        )

        self.steps_index = 2
        self.update_instructions()

    def set_end(self, item):
        i = self.parent["target"].index(item)
        self.temp_item["end"] = self.parent["name"][i]

        start_name = self.temp_item["start"]
        start_pos = self.get_pos_from_parent_name(start_name)

        end_name = self.temp_item["end"]
        end_pos = self.get_pos_from_parent_name(end_name)

        self.temp_item["arrow"].setData(start_pos.toTuple(), end_pos.toTuple())

        self.finish_temp_item()

    def finish_temp_item(self):
        if self.temp_item is None:
            return

        props = {
            "start": self.temp_item["start"],
            "end": self.temp_item["end"],
        }

        self.steps_index = 3
        self.update_instructions()
        self.set_additional_props(props)

    def set_additional_props(self, props):
        dialog = DistanceDialog(default_color=next(tab10_rgb_cycle))
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

    def shape_new_distance(self, mouse_point):
        start_name = self.temp_item["start"]
        arrow = self.temp_item["arrow"]

        start_pos = self.get_pos_from_parent_name(start_name)
        arrow.setData(start_pos.toTuple(), mouse_point.toTuple())

    def add_item(self, props):
        pen = pg.mkPen(
            color=props["color"],
            width=self.visual_preferences["distance_arrow_stem_width"],
        )
        brush = pg.mkBrush(color=props["color"])

        for n in [props["start"], props["end"]]:
            self.add_child_to_parent(n, props["name"])

        start_pos = self.get_pos_from_parent_name(props["start"])
        end_pos = self.get_pos_from_parent_name(props["end"])

        arrow = ArrowItem(
            start_pos=start_pos,
            end_pos=end_pos,
            arrow_width=self.visual_preferences["distance_arrow_head_width"],
            arrow_height=self.visual_preferences["distance_arrow_head_height"],
            stem_pen=pen,
            arrow_pen=pg.mkPen(None),
            arrow_brush=brush,
        )
        label = pg.TextItem(
            props["name"],
            anchor=(0, 0.5),
            color=pen.color(),
            fill=self.visual_preferences["item_name_label_fill_color"],
        )
        label.setPos((start_pos + end_pos) / 2)

        self.add_items_to_display([arrow, label])

        self._items["name"].append(props["name"])
        self._items["arrow"].append(arrow)
        self._items["label"].append(label)
        self._items["start"].append(props["start"])
        self._items["end"].append(props["end"])
        self._items["color"].append(props["color"])
        self._items["show"].append([True, True, True])

        logging.debug(f"Distance {props['name']} added to frame display.")

    def edit_item_props(self, name, props):
        i = self._items["name"].index(name)
        self._items["name"][i] = props["name"]
        self._items["color"][i] = props["color"]

        pen = pg.mkPen(
            color=props["color"],
            width=self.visual_preferences["distance_arrow_stem_width"],
        )
        brush = pg.mkBrush(color=props["color"])

        self._items["arrow"][i].setStemPen(pen)
        self._items["arrow"][i].setArrowPen(pen)
        self._items["arrow"][i].setArrowBrush(brush)
        self._items["label"][i].setColor(pen.color())
        self._items["label"][i].setText(props["name"])

        if props["name"] != name:
            for children in self.parent["children"]:
                if (name, "distance") in children:
                    children.remove((name, "distance"))
                    children.add((props["name"], "distance"))

    def update_item(self, name, dragged=False):
        i = self._items["name"].index(name)
        start = self._items["start"][i]
        end = self._items["end"][i]
        arrow = self._items["arrow"][i]
        label = self._items["label"][i]
        color = self._items["color"][i]

        start_pos = self.get_pos_from_parent_name(start)
        end_pos = self.get_pos_from_parent_name(end)

        arrow.setData(start_pos, end_pos)
        label.setPos((start_pos + end_pos) / 2)

        props = {
            "name": name,
            "start": start,
            "end": end,
        }
        if dragged:
            self.item_moved("distance", props)

    def start_edit_item(self, name):
        i = self._items["name"].index(name)
        color = self._items["color"][i]

        dialog = DistanceDialog(default_name=name, default_color=color)
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
