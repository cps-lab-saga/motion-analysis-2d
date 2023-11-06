from defs import QtWidgets
from motion_analysis_2d.display_widgets.plot_splitter import PlotSplitter


class XYPlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.plot_splitter = PlotSplitter(self)
        self.main_layout.addWidget(self.plot_splitter)

        self.foreground_color = self.palette().color(self.foregroundRole())
        self.markers = {}
        self.plots = {}
        for i, v in enumerate(["x", "y"]):
            self.plots[v] = self.add_plot(i, v)

    def add_plot(self, row, y_label, x_label=None):
        plot_widget = self.plot_splitter.add_plot(row=row)
        if row > 0:
            plot_widget.setXLink(self.plot_splitter[0])

        plot_widget.setLabel("left", y_label)
        if x_label is not None:
            plot_widget.setLabel("bottom", x_label)
        plot_widget.getAxis("left").setWidth(40)
        plot_widget.addLegend()

        plot_widget.setMenuEnabled(False)
        plot_widget.autoBtn.clicked.disconnect()
        plot_widget.autoBtn.clicked.connect(self.auto_range)
        plot_widget.setMouseEnabled(x=True, y=True)

        return plot_widget

    def add_line(self, param, label, color=None):
        plot_widget = self.plots[param]

        if color is None:
            color = self.foreground_color

        return plot_widget.plot(pen=color, name=label)

    def add_marker(self, name, color=None):
        self.markers[name] = {
            "x": self.add_line("x", name, color),
            "y": self.add_line("y", name, color),
        }

    def remove_marker(self, name):
        lines = self.markers.pop(name, None)
        self.plots["x"].removeItem(lines["x"])
        self.plots["y"].removeItem(lines["y"])

    def update_marker(self, name, target):
        self.markers[name]["x"].setData(target[:, 0])
        self.markers[name]["y"].setData(target[:, 1])

    def auto_range(self):
        plot_item = self.sender().parentItem()
        plot_item.enableAutoRange()

    def clear(self):
        self.markers.clear()
        for p in self.plots.values():
            p.clear()

    def gui_save(self, settings):
        self.plot_splitter.gui_save(settings)

    def gui_restore(self, settings):
        self.plot_splitter.gui_restore(settings)


if __name__ == "__main__":
    import numpy as np

    sample_data = np.array(range(25))

    app = QtWidgets.QApplication([])
    widget = XYPlotWidget()
    widget.show()

    app.exec()
