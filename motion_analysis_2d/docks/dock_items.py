from functools import partial

import qtawesome as qta
from superqt import QCollapsible

from defs import QtWidgets, QtGui, Signal
from motion_analysis_2d.custom_components import BaseDock


class ItemsDock(BaseDock):
    item_added = Signal(str, object, str)
    item_modified = Signal(str, object, str)
    item_removed = Signal(str, str)

    show_item = Signal(str, str)
    hide_item = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Items")

        self.rows = {}
        self.collapsibles = {}

        self.add_item_type("marker")
        self.add_item_type("angle")
        self.add_item_type("distance")

    def add_item_type(self, item_type):
        collapsible = QCollapsible(item_type.capitalize())
        collapsible.expand(False)
        self.dock_layout.addWidget(collapsible)
        self.collapsibles[item_type] = collapsible
        self.rows[item_type] = {}

    def add_row(self, name, color, item_type):
        row = ItemsRow(name, color, item_type, parent=self)
        row.checkbox_toggled.connect(partial(self.checkbox_toggled, item_type))
        self.rows[item_type][name] = row
        self.collapsibles[item_type].addWidget(row)

    def remove_row(self, name, item_type):
        row = self.rows[item_type].pop(name)
        self.collapsibles[item_type].removeWidget(row)
        row.deleteLater()

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

    def __init__(self, name, color, item_type="marker", parent=None):
        super().__init__(parent)

        self.name = name
        self.color = color
        self.item_type = item_type

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 11, 0)

        self.checkbox = QtWidgets.QCheckBox(self)
        self.checkbox.setText(self.name)
        self.checkbox.setChecked(True)
        if item_type == "marker":
            self.checkbox.setIcon(
                qta.icon("mdi6.square-outline", color=QtGui.QColor(*self.color))
            )
        elif item_type == "angle":
            self.checkbox.setIcon(
                qta.icon("mdi6.angle-acute", color=QtGui.QColor(*self.color))
            )
        elif item_type == "distance":
            self.checkbox.setIcon(
                qta.icon("mdi6.ruler", color=QtGui.QColor(*self.color))
            )
        self.checkbox.toggled.connect(partial(self.checkbox_toggled.emit, name))
        self.main_layout.addWidget(self.checkbox)

        self.main_layout.addStretch()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dock = ItemsDock()
    dock.add_row("test", (44, 160, 44), "distance")
    dock.add_row("test", (44, 160, 44), "angle")
    dock.add_row("test", (44, 160, 44), "marker")
    dock.show()

    app.exec()
