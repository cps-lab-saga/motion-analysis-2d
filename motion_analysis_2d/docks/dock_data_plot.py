from defs import QtWidgets
from motion_analysis_2d.custom_components import BaseDock
from motion_analysis_2d.display_widgets import XYPlotWidget


class DataPlotDock(BaseDock):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Data Plots")

        self.xy_plot_widget = XYPlotWidget(self)
        self.dock_layout.addWidget(self.xy_plot_widget)

        self.add_marker = self.xy_plot_widget.add_marker
        self.remove_marker = self.xy_plot_widget.remove_marker
        self.update_marker = self.xy_plot_widget.update_marker
        self.move_frame_line = self.xy_plot_widget.move_frame_line
        self.set_frame_bound = self.xy_plot_widget.set_frame_bound
        self.set_frame_line_draggable = self.xy_plot_widget.set_frame_line_draggable
        self.frame_line_dragged = self.xy_plot_widget.frame_line_dragged
        self.clear = self.xy_plot_widget.clear


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dock = DataPlotDock()
    dock.show()

    app.exec()
