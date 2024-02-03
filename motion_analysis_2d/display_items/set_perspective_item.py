import numpy as np
import pyqtgraph as pg

from motion_analysis_2d.custom_components import (
    PerspectiveItem,
)
from motion_analysis_2d.dialogs import PerspectiveDialog
from motion_analysis_2d.funcs import offset_at_centre
from .base_item_display import BaseDisplayItem


class SetPerspectiveItem(BaseDisplayItem):
    def __init__(self, display, new_item_pen, visual_settings):
        super().__init__(display, new_item_pen, visual_settings)

        self.item_type_name = "set_perspective"
        self.temp_item = None

        self.steps = (
            "Starting...",
            "Adjust perspective.",
        )
        self.steps_index = 0

    def start_item_suggestion(self):
        # temporarily remove other items
        self.hide_all_items()

        im_x, im_y, im_w, im_h = self.get_image_size()
        (w, _), (_, h) = self.get_pixel_vectors()
        item = PerspectiveItem(
            inner_corners=(
                (im_w * 0.2, im_h * 0.2),
                (im_w * 0.2, im_h * 0.8),
                (im_w * 0.8, im_h * 0.8),
                (im_w * 0.8, im_h * 0.2),
            ),
            outer_offsets=(im_w * 0.1, im_h * 0.1, im_w * 0.1, im_h * 0.1),
            inner_pen=pg.mkPen(
                color=self.visual_settings["set_perspective_inner_pen_color"],
                width=self.visual_settings["set_perspective_inner_pen_width"],
            ),
            inner_hover_pen=pg.mkPen(
                color=self.visual_settings["set_perspective_inner_hover_pen_color"],
                width=self.visual_settings["set_perspective_inner_hover_pen_width"],
            ),
            outer_pen=pg.mkPen(
                color=self.visual_settings["set_perspective_outer_pen_color"],
                width=self.visual_settings["set_perspective_outer_pen_width"],
            ),
            outer_hover_pen=pg.mkPen(
                color=self.visual_settings["set_perspective_outer_hover_pen_color"],
                width=self.visual_settings["set_perspective_outer_hover_pen_width"],
            ),
        )
        item.sigInnerCornerMoved.connect(self.perspective_corner_moved)
        item.sigMoved.connect(self.perspective_moved)

        x_label = pg.TextItem(
            "x",
            anchor=(0.5, 0.5),
            color=self.visual_settings["set_perspective_inner_pen_color"],
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        y_label = pg.TextItem(
            "y",
            anchor=(0.5, 0.5),
            color=self.visual_settings["set_perspective_inner_pen_color"],
            fill=self.visual_settings["item_name_label_fill_color"],
        )
        inner_corners = item.get_params()["inner_corners"]
        x_label.setPos(*offset_at_centre(inner_corners[3], inner_corners[0], 5 * h))
        y_label.setPos(*offset_at_centre(inner_corners[0], inner_corners[1], 5 * w))

        dialog = PerspectiveDialog()
        dialog.completed.connect(self.finish_temp_item)
        dialog.rejected.connect(self.emit_end_new_settings)

        self.temp_item = {
            "item": item,
            "x_label": x_label,
            "y_label": y_label,
            "dialog": dialog,
        }
        dialog.show()

        self.add_items_to_display(
            [
                self.temp_item["item"],
                self.temp_item["x_label"],
                self.temp_item["y_label"],
            ]
        )

        self.steps_index = 1
        self.update_instructions()

    def reset_temp_item(self):
        if self.temp_item is not None:
            self.remove_items_from_display(
                [
                    self.temp_item["item"],
                    self.temp_item["x_label"],
                    self.temp_item["y_label"],
                ]
            )
            # restore temporarily removed items
            self.show_all_items()

            self.temp_item = None
            self.steps_index = 0
            self.update_instructions()

    def perspective_corner_moved(self, i, point):
        if self.temp_item is None:
            return

        x, y = self.keep_point_in_frame(*point)
        (w, _), (_, h) = self.get_pixel_vectors()
        self.temp_item["item"].setInnerCorner(i, (x, y))

        inner_corners = self.temp_item["item"].get_params()["inner_corners"]
        self.temp_item["x_label"].setPos(
            *offset_at_centre(inner_corners[3], inner_corners[0], 5 * h)
        )
        self.temp_item["y_label"].setPos(
            *offset_at_centre(inner_corners[0], inner_corners[1], 5 * h)
        )

    def perspective_moved(self, inner_corners):
        im_x, im_y, im_w, im_h = self.get_image_size()
        (w, _), (_, h) = self.get_pixel_vectors()

        new_corners = np.array(inner_corners)
        if (new_corners[:, 0] >= (im_x + im_w)).any():
            new_corners[:, 0] = new_corners[:, 0] - (
                new_corners[:, 0].max() - (im_x + im_w) + 1
            )
        elif (new_corners[:, 0] <= im_x).any():
            new_corners[:, 0] = new_corners[:, 0] + (im_x - new_corners[:, 0].min()) - 1
        if (new_corners[:, 1] >= (im_y + im_h)).any():
            new_corners[:, 1] = (
                new_corners[:, 1] - (new_corners[:, 1].max() - (im_y + im_h)) + 1
            )
        elif (new_corners[:, 1] <= im_y).any():
            new_corners[:, 1] = new_corners[:, 1] + (im_y - new_corners[:, 1].min()) - 1
        self.temp_item["item"].setData(inner_corners=new_corners.tolist())

        self.temp_item["x_label"].setPos(
            *offset_at_centre(new_corners[3], new_corners[0], 5 * h)
        )
        self.temp_item["y_label"].setPos(
            *offset_at_centre(new_corners[0], new_corners[1], 5 * h)
        )

    def finish_temp_item(self, x, y):
        if self.temp_item is None:
            return

        inner_corners, outer_corners, outer_offsets = (
            self.temp_item["item"].get_params().values()
        )
        img_points = np.array(inner_corners)
        boundary_points = np.array(outer_corners)

        x_pixel = np.linalg.norm(img_points[0] - img_points[3])
        y_pixel = np.linalg.norm(img_points[1] - img_points[0])

        if x == 0:
            x = x_pixel
        if y == 0:
            y = y_pixel

        obj_points = np.array([(0, 0), (0, y), (x, y), (x, 0)])
        pixel_per_real = np.array((x_pixel / x, y_pixel / y))

        pixel_offset = img_points[0] - boundary_points[0]
        real_offset = pixel_offset / pixel_per_real

        final_obj_points = obj_points + real_offset

        w = boundary_points[0] - boundary_points[3]
        w_real = np.abs(np.linalg.norm(w / pixel_per_real))

        h = boundary_points[1] - boundary_points[0]
        h_real = np.abs(np.linalg.norm(h / pixel_per_real))

        output_size_real = [w_real, h_real]

        props = {
            "img_points": img_points,
            "obj_points": final_obj_points,
            "output_size": output_size_real,
        }
        self.reset_temp_item()
        self.emit_new_settings(props)

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
