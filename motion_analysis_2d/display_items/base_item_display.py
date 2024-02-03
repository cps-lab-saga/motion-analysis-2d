import logging

from motion_analysis_2d.funcs import prevent_name_collision


class BaseDisplayItem:
    def __init__(self, display, new_item_pen, visual_settings, parent=None):
        self.parent = parent
        self.display = display
        self.new_item_pen = new_item_pen
        self.visual_settings = visual_settings
        self.steps = [""]
        self.display_item_types = []
        self.display_item_names = []
        self.parent_item_names = []
        self.steps_index = 0

        self._items = None
        self.temp_item = None
        self.item_type_name = "base"

    def reset_temp_item(self):
        pass

    def start_item_suggestion(self):
        pass

    def finish_temp_item(self, *args, **kwargs):
        pass

    def edit_item_props(self, name, props):
        pass

    def remove_selected_item(self, item):
        for a in self.display_item_names:
            if item in self._items[a]:
                i = self._items[a].index(item)
                name = self._items["name"][i]
                self.suggest_removal(name)
                return True
        return False

    def suggest_removal(self, name):
        self.display.item_removal_suggested.emit(self.item_type_name, name)

    def get_image_size(self):
        return self.display.get_image_size()

    def get_pixel_vectors(self):
        return self.display.fig.pixelVectors()

    def current_instruction(self):
        if self.steps_index < len(self.steps):
            return self.steps[self.steps_index]
        else:
            return None

    def update_instructions(self):
        self.display.update_instructions(self.current_instruction())

    def add_items_to_display(self, items):
        for item in items:
            self.display.fig.addItem(item)

    def remove_items_from_display(self, items):
        for item in items:
            self.display.fig.removeItem(item)

    def mouse_clicked(self, mouse_point, items):
        pass

    def mouse_moved(self, mouse_point):
        pass

    def emit_new_item(self, item_props):
        self.display.new_item_suggested.emit(self.item_type_name, item_props)
        logging.debug(f"New {self.item_type_name} suggested, {item_props}.")

    def emit_edit_item(self, original_name, item_props):
        self.display.edit_item_suggested.emit(
            self.item_type_name, original_name, item_props
        )
        logging.debug(
            f"Edit {self.item_type_name} {original_name} suggested, {item_props}."
        )

    def emit_new_settings(self, props):
        self.display.new_settings_suggested.emit(self.item_type_name, props)

    def emit_end_new_settings(self):
        self.display.new_settings_ended.emit()

    def item_moved(self, item_type, item_props):
        self.display.item_moved.emit(item_type, item_props)
        logging.debug(f"Item {item_type} moved in frame display, {item_props}.")

    def frame_shape_changed(self):
        pass

    def update_child_item(self, child_type, child_name, **kwargs):
        self.display.update_child_item(child_type, child_name, **kwargs)

    def update_parents_of_child(
        self, child_type, child_name, old_parent_name, new_parent_name
    ):
        self.display.update_parents_of_child(
            child_type, child_name, old_parent_name, new_parent_name
        )

    def change_parent(self, name, parent_name, new_parent_name):
        i = self._items["name"].index(name)
        for x in self.parent_item_names:
            if self._items[x][i] == parent_name:
                self._items[x][i] = new_parent_name

    def hide_all_items(self):
        self.display.hide_all_items()

    def show_all_items(self):
        self.display.show_all_items()

    def clear(self):
        for l in self._items.values():
            l.clear()

    def prevent_name_collision(self, name):
        return prevent_name_collision(name, self._items["name"])

    def __getitem__(self, item):
        return self._items[item]

    def items(self):
        return self._items.items()

    def remove_item(self, name):
        i = self._items["name"].index(name)
        if all(self._items["show"][i]):
            self.remove_items_from_display(
                [self._items[x][i] for x in self.display_item_names]
            )

        if "children" in self._items:
            all_children = self._items["children"][i].copy()
            for child_name, child_type in all_children:
                self.display.item_removal_suggested.emit(child_type, child_name)

        if self.parent is not None:
            for n in self.parent_item_names:
                self.remove_child_from_parent(self._items[n][i], name)

        for item in self._items.values():
            item.pop(i)

        logging.debug(
            f"{self.item_type_name.capitalize()} {name} removed from frame display."
        )

    def add_child_to_parent(self, parent_name, name):
        i = self.parent["name"].index(parent_name)
        if (name, self.item_type_name) not in self.parent["children"][i]:
            self.parent["children"][i].add((name, self.item_type_name))
        logging.debug(f"Child {(name, self.item_type_name)} added to {parent_name}.")

    def remove_child_from_parent(self, parent_name, name):
        i = self.parent["name"].index(parent_name)
        self.parent["children"][i].discard((name, self.item_type_name))
        logging.debug(
            f"Child {(name, self.item_type_name)} removed from {parent_name}."
        )

    def hide_item(self, name, index=0):
        i = self._items["name"].index(name)
        assert index < len(self._items["show"][i]), "Invalid index!"

        if not all(self._items["show"][i]):
            self._items["show"][i][index] = False
            return  # already hidden
        else:
            self.remove_items_from_display(
                [self._items[x][i] for x in self.display_item_names]
            )
            self._items["show"][i][index] = False
            logging.debug(
                f"{self.item_type_name.capitalize()} {name} hidden in frame display."
            )

    def show_item(self, name, index=0):
        i = self._items["name"].index(name)
        assert index < len(self._items["show"][i]), "Invalid index!"

        if all(self._items["show"][i]):
            self._items["show"][i][index] = True
            return  # already shown
        else:
            self._items["show"][i][index] = True
            if all(self._items["show"][i]):
                self.add_items_to_display(
                    [self._items[x][i] for x in self.display_item_names]
                )
                logging.debug(
                    f"{self.item_type_name.capitalize()} {name} shown in frame display."
                )

    def set_data(self, name, data):
        pass
