import logging

from defs import QtWidgets, Signal
from motion_analysis_2d.custom_components import BaseDock
from motion_analysis_2d.display_widgets import DataPlotWidget


class DataPlotDock(BaseDock):
    frame_line_dragged = Signal(int)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Data Plots")

        self.plot_widgets = {}
        self.trackers = {}
        self.angles = {}
        self.distances = {}

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.button_layout = QtWidgets.QHBoxLayout()
        self.dock_layout.addLayout(self.button_layout)

        self.stacked_layout = QtWidgets.QStackedLayout()
        self.dock_layout.addLayout(self.stacked_layout)

        self.plot_widgets["Trackers"] = DataPlotWidget(plots=["x", "y"], parent=self)
        self.plot_widgets["Trackers"].frame_line_dragged.connect(
            self.plot_frame_line_dragged
        )
        self.stacked_layout.addWidget(self.plot_widgets["Trackers"])

        self.plot_widgets["Angles"] = DataPlotWidget(plots=["θ"], parent=self)
        self.plot_widgets["Angles"].frame_line_dragged.connect(
            self.plot_frame_line_dragged
        )
        self.stacked_layout.addWidget(self.plot_widgets["Angles"])

        self.plot_widgets["Distances"] = DataPlotWidget(plots=["x", "y"], parent=self)
        self.plot_widgets["Distances"].frame_line_dragged.connect(
            self.plot_frame_line_dragged
        )
        self.stacked_layout.addWidget(self.plot_widgets["Distances"])

        self.buttons = []
        for page in self.plot_widgets.keys():
            self.make_button(page)
        self.buttons[0].setChecked(True)
        self.button_layout.addStretch()

    def move_frame_line(self, x):
        for plot_widget in self.plot_widgets.values():
            plot_widget.move_frame_line(x)

    def set_frame_bound(self, bounds):
        for plot_widget in self.plot_widgets.values():
            plot_widget.set_frame_bound(bounds)

    def plot_frame_line_dragged(self, frame_no):
        sender = self.sender()
        for plot_widget in self.plot_widgets.values():
            if plot_widget is not sender:
                plot_widget.move_frame_line(frame_no)
        self.frame_line_dragged.emit(frame_no)

    def set_frame_line_draggable(self, draggable):
        for plot_widget in self.plot_widgets.values():
            plot_widget.set_frame_line_draggable(draggable)

    def add_tracker(self, name, color=None):
        self.trackers[name] = {
            "x": self.plot_widgets["Trackers"].add_line("x", label=name, color=color),
            "y": self.plot_widgets["Trackers"].add_line("y", label=name, color=color),
        }
        logging.debug(f"Tracker {name} added to data plot dock.")

    def edit_tracker(self, name, new_name, new_color):
        if new_name != name:
            self.trackers[new_name] = self.trackers[name]
            del self.trackers[name]

        self.trackers[new_name]["x"].setData(pen=new_color)
        self.trackers[new_name]["y"].setData(pen=new_color)

        self.plot_widgets["Trackers"].lines["x"][new_name] = self.plot_widgets[
            "Trackers"
        ].lines["x"][name]
        self.plot_widgets["Trackers"].lines["y"][new_name] = self.plot_widgets[
            "Trackers"
        ].lines["y"][name]
        del self.plot_widgets["Trackers"].lines["x"][name]
        del self.plot_widgets["Trackers"].lines["y"][name]

    def show_tracker(self, name):
        self.plot_widgets["Trackers"].show_line("x", name)
        self.plot_widgets["Trackers"].show_line("y", name)

    def hide_tracker(self, name):
        self.plot_widgets["Trackers"].hide_line("x", name)
        self.plot_widgets["Trackers"].hide_line("y", name)

    def remove_tracker(self, name):
        self.trackers.pop(name, None)
        self.plot_widgets["Trackers"].remove_line("x", name)
        self.plot_widgets["Trackers"].remove_line("y", name)
        logging.debug(f"Tracker {name} removed from data plot dock.")

    def update_tracker(self, name, target, frames=None):
        self.plot_widgets["Trackers"].update_line("x", name, target[:, 0], frames)
        self.plot_widgets["Trackers"].update_line("y", name, target[:, 1], frames)

    def add_angle(self, name, color=None):
        self.angles[name] = {
            "θ": self.plot_widgets["Angles"].add_line("θ", name, color),
        }
        logging.debug(f"Angle {name} added to data plot dock.")

    def edit_angle(self, name, new_name, new_color):
        if new_name != name:
            self.angles[new_name] = self.angles[name]
            del self.angles[name]

        self.angles[new_name]["θ"].setData(pen=new_color)

        self.plot_widgets["Angles"].lines["θ"][new_name] = self.plot_widgets[
            "Angles"
        ].lines["θ"][name]
        del self.plot_widgets["Angles"].lines["θ"][name]

    def show_angle(self, name):
        self.plot_widgets["Angles"].show_line("θ", name)

    def hide_angle(self, name):
        self.plot_widgets["Angles"].hide_line("θ", name)

    def remove_angle(self, name):
        self.angles.pop(name, None)
        self.plot_widgets["Angles"].remove_line("θ", name)
        logging.debug(f"Angle {name} removed from data plot dock.")

    def update_angle(self, name, angle, frames=None):
        self.plot_widgets["Angles"].update_line("θ", name, angle, frames)

    def add_distance(self, name, color=None):
        self.distances[name] = {
            "x": self.plot_widgets["Distances"].add_line("x", name, color),
            "y": self.plot_widgets["Distances"].add_line("y", name, color),
        }
        logging.debug(f"Distance {name} added to data plot dock.")

    def edit_distance(self, name, new_name, new_color):
        if new_name != name:
            self.distances[new_name] = self.distances[name]
            del self.distances[name]

        self.distances[new_name]["x"].setData(pen=new_color)
        self.distances[new_name]["y"].setData(pen=new_color)

        self.plot_widgets["Distances"].lines["x"][new_name] = self.plot_widgets[
            "Distances"
        ].lines["x"][name]
        self.plot_widgets["Distances"].lines["y"][new_name] = self.plot_widgets[
            "Distances"
        ].lines["y"][name]
        del self.plot_widgets["Distances"].lines["x"][name]
        del self.plot_widgets["Distances"].lines["y"][name]

    def show_distance(self, name):
        self.plot_widgets["Distances"].show_line("x", name)
        self.plot_widgets["Distances"].show_line("y", name)

    def hide_distance(self, name):
        self.plot_widgets["Distances"].hide_line("x", name)
        self.plot_widgets["Distances"].hide_line("y", name)

    def remove_distance(self, name):
        self.distances.pop(name, None)
        self.plot_widgets["Distances"].remove_line("x", name)
        self.plot_widgets["Distances"].remove_line("y", name)
        logging.debug(f"Distance {name} removed from data plot dock.")

    def update_distance(self, name, distance, frames=None):
        self.plot_widgets["Distances"].update_line("x", name, distance[:, 0], frames)
        self.plot_widgets["Distances"].update_line("y", name, distance[:, 1], frames)

    def make_button(self, text):
        button = QtWidgets.QPushButton(text, self)
        button.setFlat(True)
        button.setCheckable(True)
        button.toggled.connect(self.switch_page)
        self.buttons.append(button)
        self.button_group.addButton(button)
        self.button_layout.addWidget(button)
        return button

    def switch_page(self):
        i = self.buttons.index(self.button_group.checkedButton())
        self.stacked_layout.setCurrentIndex(i)

    def clear(self):
        for plot_widget in self.plot_widgets.values():
            plot_widget.clear()

    def change_layout_based_on_dock_area(self, area):
        self.dock_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        self.layout_direction_changed.emit(QtWidgets.QBoxLayout.TopToBottom)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dock = DataPlotDock()
    dock.set_frame_line_draggable(True)
    dock.show()

    app.exec()
