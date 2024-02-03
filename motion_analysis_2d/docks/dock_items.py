import logging
from functools import partial

import qtawesome as qta
from superqt import QCollapsible

from defs import QtCore, QtWidgets, QtGui, Signal
from motion_analysis_2d.custom_components import BaseDock


class ItemsDock(BaseDock):
    edit_item_suggested = Signal(str, str)
    remove_item_suggested = Signal(str, str)

    show_item = Signal(str, str)
    hide_item = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Items")

        self.rows = {}
        self.collapsibles = {}

        self.add_item_type("tracker")
        self.add_item_type("angle")
        self.add_item_type("distance")

    def add_item_type(self, item_type):
        collapsible = QCollapsible(item_type.capitalize())
        collapsible.expand(animate=False)
        self.dock_layout.addWidget(collapsible)
        self.collapsibles[item_type] = collapsible
        self.rows[item_type] = {}

    def add_row(self, item_type, item_props):
        name = item_props["name"]
        color = item_props["color"]

        row = ItemsRow(name, color, item_type, parent=self)
        row.checkbox_toggled.connect(partial(self.checkbox_toggled, item_type))
        row.edit_item_suggested.connect(self.edit_item_suggested.emit)
        row.remove_item_suggested.connect(self.remove_item_suggested.emit)
        self.rows[item_type][name] = row
        self.collapsibles[item_type].addWidget(row)
        logging.debug(f"{item_type.capitalize()} {name} added to items dock.")

    def edit_row(self, item_type, name, props):
        if props["name"] != name:
            self.rows[item_type][props["name"]] = self.rows[item_type][name]
            del self.rows[item_type][name]

        self.rows[item_type][props["name"]].set_props(
            props["name"], item_type, props["color"]
        )

    def remove_row(self, item_type, name):
        row = self.rows[item_type].pop(name)
        self.collapsibles[item_type].removeWidget(row)
        row.deleteLater()
        logging.debug(f"{item_type.capitalize()} {name} removed from items dock.")

    def checkbox_toggled(self, item_type, name, show):
        if show:
            self.show_item.emit(item_type, name)
        else:
            self.hide_item.emit(item_type, name)

    def clear(self):
        for item_type, rows in self.rows.items():
            for row in rows.values():
                self.collapsibles[item_type].removeWidget(row)
                row.deleteLater()
            self.rows[item_type].clear()


class ItemsRow(QtWidgets.QWidget):
    checkbox_toggled = Signal(str, object)
    edit_item_suggested = Signal(str, object)
    remove_item_suggested = Signal(str, object)

    def __init__(self, name, color, item_type="tracker", parent=None):
        super().__init__(parent)

        self.name = name
        self.color = color
        self.item_type = item_type

        self.context_menu = QtWidgets.QMenu(self)
        edit_action = self.context_menu.addAction("Edit")
        edit_action.setIcon(qta.icon("mdi6.pencil"))
        edit_action.triggered.connect(self.emit_edit_item)
        delete_action = self.context_menu.addAction("Remove")
        delete_action.setIcon(qta.icon("mdi6.close", color="red"))
        delete_action.triggered.connect(self.emit_remove_item)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 11, 0)

        self.checkbox = QtWidgets.QCheckBox(self)
        self.checkbox.setChecked(True)
        self.checkbox.toggled.connect(partial(self.checkbox_toggled.emit, self.name))

        self.set_props(name, item_type, color)
        self.main_layout.addWidget(self.checkbox)

        self.main_layout.addStretch()

    def set_props(self, name, item_type, color):
        self.name = name
        self.color = color
        self.item_type = item_type

        self.checkbox.setText(name)
        self.checkbox.toggled.disconnect()
        self.checkbox.toggled.connect(partial(self.checkbox_toggled.emit, self.name))

        if item_type == "tracker":
            self.checkbox.setIcon(
                qta.icon("mdi6.square-outline", color=QtGui.QColor(*color))
            )
        elif item_type == "angle":
            self.checkbox.setIcon(
                qta.icon("mdi6.angle-acute", color=QtGui.QColor(*color))
            )
        elif item_type == "distance":
            self.checkbox.setIcon(qta.icon("mdi6.ruler", color=QtGui.QColor(*color)))

    def context_menu_requested(self, pos):
        self.context_menu.exec(QtGui.QCursor.pos())

    def emit_edit_item(self):
        self.edit_item_suggested.emit(self.item_type, self.name)

    def emit_remove_item(self):
        self.remove_item_suggested.emit(self.item_type, self.name)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dock = ItemsDock()
    dock.add_row("test_distance", (44, 160, 44), "distance")
    dock.add_row("test_angle", (44, 160, 44), "angle")
    dock.add_row("test_tracker", (44, 160, 44), "tracker")
    dock.edit_row("test_tracker", "test2", (44, 160, 44), "tracker")
    dock.show()

    app.exec()
