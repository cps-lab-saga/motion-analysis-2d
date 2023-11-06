from functools import partial

import qtawesome as qta
from superqt import QCollapsible

from defs import QtWidgets, QtGui, Signal
from motion_analysis_2d.custom_components import BaseDock
from motion_analysis_2d.display_widgets import XYPlotWidget


class XYPlotDock(BaseDock):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("XY Plot")

        self.xy_plot_widget = XYPlotWidget(self)
        self.dock_layout.addWidget(self.xy_plot_widget)

        self.add_marker = self.xy_plot_widget.add_marker
        self.remove_marker = self.xy_plot_widget.remove_marker
        self.update_marker = self.xy_plot_widget.update_marker
        self.clear = self.xy_plot_widget.clear


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    dock = XYPlotDock()
    dock.show()

    app.exec()
