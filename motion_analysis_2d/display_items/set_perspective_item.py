import numpy as np
import pyqtgraph as pg

from motion_analysis_2d.custom_components import PerspectiveItem, LengthItem
from motion_analysis_2d.dialogs import PerspectiveDialog
from motion_analysis_2d.funcs import offset_at_centre
from .base_item_display import BaseDisplayItem


class SetPerspectiveItem(BaseDisplayItem):
    def __init__(self, display, new_item_pen, visual_preferences):
        super().__init__(display, new_item_pen, visual_preferences)

        self.item_type_name = "set_perspective"
        self.temp_item = None
        self.dialog = None
        self.mode = ""

        self.steps = (
            "Starting...",
            "Adjust perspective / scaling.",
        )
        self.steps_index = 0

    def start_dialog(self):
        self.dialog = PerspectiveDialog()
        self.dialog.mode_changed.connect(self.mode_changed)
        self.dialog.completed.connect(self.finish_temp_item)
        self.dialog.rejected.connect(self.emit_end_new_settings)
        self.mode_changed()
        self.dialog.show()

    def mode_changed(self, mode=None):
        if mode is None:
            self.mode = self.dialog.mode()
        else:
            self.mode = mode

        if self.temp_item is not None:
            self.remove_items_from_display(
                [
                    self.temp_item["item"],
                    *[item for item in self.temp_item["labels"]],
                ]
            )
            self.temp_item = None

        if self.mode == "Perspective":
            self.temp_item = self.setup_perspective()

        elif self.mode == "Scaling":
            self.temp_item = self.setup_length()

        else:
            raise ValueError("Unknown mode")

        self.add_items_to_display(
            [
                self.temp_item["item"],
                *[item for item in self.temp_item["labels"]],
            ]
        )
        self.steps_index = 1
        self.update_instructions()

    def setup_perspective(self):
        im_x, im_y, im_w, im_h = self.get_image_size()
        (w, _), (_, h) = self.get_pixel_vectors()
        perspective_item = PerspectiveItem(
            inner_corners=(
                (im_w * 0.2, im_h * 0.2),
                (im_w * 0.2, im_h * 0.8),
                (im_w * 0.8, im_h * 0.8),
                (im_w * 0.8, im_h * 0.2),
            ),
            outer_offsets=(im_w * 0.1, im_h * 0.1, im_w * 0.1, im_h * 0.1),
            inner_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_inner_pen_color"],
                width=self.visual_preferences["set_perspective_inner_pen_width"],
            ),
            inner_hover_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_inner_hover_pen_color"],
                width=self.visual_preferences["set_perspective_inner_hover_pen_width"],
            ),
            outer_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_outer_pen_color"],
                width=self.visual_preferences["set_perspective_outer_pen_width"],
            ),
            outer_hover_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_outer_hover_pen_color"],
                width=self.visual_preferences["set_perspective_outer_hover_pen_width"],
            ),
        )
        perspective_item.sigInnerCornerMoved.connect(self.perspective_corner_moved)
        perspective_item.sigMoved.connect(self.perspective_moved)

        x_label = pg.TextItem(
            "x",
            anchor=(0.5, 0.5),
            color=self.visual_preferences["set_perspective_inner_pen_color"],
            fill=self.visual_preferences["item_name_label_fill_color"],
        )
        y_label = pg.TextItem(
            "y",
            anchor=(0.5, 0.5),
            color=self.visual_preferences["set_perspective_inner_pen_color"],
            fill=self.visual_preferences["item_name_label_fill_color"],
        )
        inner_corners = perspective_item.get_params()["inner_corners"]
        x_label.setPos(*offset_at_centre(inner_corners[3], inner_corners[0], 5 * h))
        y_label.setPos(*offset_at_centre(inner_corners[0], inner_corners[1], 5 * w))

        return {
            "item": perspective_item,
            "labels": [x_label, y_label],
        }

    def setup_length(self):
        im_x, im_y, im_w, im_h = self.get_image_size()
        (w, _), (_, h) = self.get_pixel_vectors()
        length_item = LengthItem(
            line_corners=((im_w * 0.2, im_h * 0.5), (im_w * 0.8, im_h * 0.5)),
            line_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_inner_pen_color"],
                width=self.visual_preferences["set_perspective_inner_pen_width"],
            ),
            line_hover_pen=pg.mkPen(
                color=self.visual_preferences["set_perspective_inner_hover_pen_color"],
                width=self.visual_preferences["set_perspective_inner_hover_pen_width"],
            ),
        )
        length_item.sigLineCornerMoved.connect(self.line_corner_moved)
        length_item.sigMoved.connect(self.line_moved)

        distance_label = pg.TextItem(
            "Real distance",
            anchor=(0.5, 0.5),
            color=self.visual_preferences["set_perspective_inner_pen_color"],
            fill=self.visual_preferences["item_name_label_fill_color"],
        )
        line_corners = length_item.get_params()
        distance_label.setPos(*offset_at_centre(line_corners[0], line_corners[1], 0))

        return {
            "item": length_item,
            "labels": [distance_label],
        }

    def start_item_suggestion(self):
        # temporarily remove other items
        self.hide_all_items()
        self.start_dialog()

    def reset_temp_item(self):
        if self.temp_item is not None:
            self.remove_items_from_display(
                [
                    self.temp_item["item"],
                    *[item for item in self.temp_item["labels"]],
                ]
            )

            if self.dialog is not None:
                self.dialog.close()
                self.dialog = None

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
        self.temp_item["labels"][0].setPos(
            *offset_at_centre(inner_corners[3], inner_corners[0], 5 * h)
        )
        self.temp_item["labels"][1].setPos(
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

        self.temp_item["labels"][0].setPos(
            *offset_at_centre(new_corners[3], new_corners[0], 5 * h)
        )
        self.temp_item["labels"][1].setPos(
            *offset_at_centre(new_corners[0], new_corners[1], 5 * h)
        )

    def line_corner_moved(self, i, point):
        if self.temp_item is None:
            return

        x, y = self.keep_point_in_frame(*point)
        (w, _), (_, h) = self.get_pixel_vectors()
        self.temp_item["item"].setLineCorner(i, (x, y))

        line_corners = self.temp_item["item"].get_params()
        self.temp_item["labels"][0].setPos(
            *offset_at_centre(line_corners[0], line_corners[1], 0)
        )

    def line_moved(self, line_corners):
        im_x, im_y, im_w, im_h = self.get_image_size()
        (w, _), (_, h) = self.get_pixel_vectors()

        new_corners = np.array(line_corners)
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
        self.temp_item["item"].setData(line_corners=new_corners.tolist())

        self.temp_item["labels"][0].setPos(
            *offset_at_centre(line_corners[0], line_corners[1], 0)
        )

    def finish_perspective_item(self, params):
        inner_corners, outer_corners, outer_offsets = (
            self.temp_item["item"].get_params().values()
        )
        img_points = np.array(inner_corners)
        boundary_points = np.array(outer_corners)

        x_pixel = np.linalg.norm(img_points[0] - img_points[3])
        y_pixel = np.linalg.norm(img_points[1] - img_points[0])

        x, y = params
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
        return props

    def finish_length_item(self, params):
        line_corners = self.temp_item["item"].get_params()
        img_points = np.array(line_corners)

        (real_length,) = params

        props = {
            "img_points": img_points,
            "real_distance": real_length,
        }
        return props

    def finish_temp_item(self, mode, params):
        if self.temp_item is None:
            return

        if mode == "Perspective":
            props = self.finish_perspective_item(params)
        elif mode == "Scaling":
            props = self.finish_length_item(params)
        else:
            raise ValueError("Unknown mode")

        props["mode"] = mode

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
