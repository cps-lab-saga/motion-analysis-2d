import pyqtgraph as pg

from defs import QtWidgets, Signal
from motion_analysis_2d.custom_components import tab10_rgb
from motion_analysis_2d.display_widgets.plot_splitter import PlotSplitter


class XYPlotWidget(QtWidgets.QWidget):
    frame_line_dragged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.plot_splitter = PlotSplitter(self)
        self.main_layout.addWidget(self.plot_splitter)

        self.foreground_color = self.palette().color(self.foregroundRole())
        self.frame_pen = pg.mkPen(color=tab10_rgb["purple"], width=1)
        self.frame_hover_pen = pg.mkPen(color=tab10_rgb["purple"], width=3)

        self.markers = {}
        self.plots = {}
        self.frame_lines = {}
        for i, v in enumerate(["x", "y"]):
            self.plots[v] = self.add_plot(i, v)
            self.frame_lines[v] = self.add_current_frame_line(self.plots[v])

    def add_plot(self, row, y_label, x_label=None):
        plot_widget = self.plot_splitter.add_plot(row=row)
        if row > 0:
            plot_widget.setXLink(self.plot_splitter[0])

        plot_widget.setLabel("left", y_label)
        if x_label is not None:
            plot_widget.setLabel("bottom", x_label)
        plot_widget.getAxis("left").setWidth(60)
        plot_widget.addLegend(offset=(-1, 1))

        plot_widget.setMenuEnabled(False)
        plot_widget.autoBtn.clicked.disconnect()
        plot_widget.autoBtn.clicked.connect(self.auto_range)
        plot_widget.setMouseEnabled(x=True, y=True)

        return plot_widget

    def add_current_frame_line(self, plot_widget):
        line = pg.InfiniteLine(
            pen=self.frame_pen,
            hoverPen=self.frame_hover_pen,
            movable=True,
        )
        line.sigDragged.connect(self.frame_line_moved)
        plot_widget.addItem(line)
        return line

    def frame_line_moved(self, dragged_line):
        frame_no = round(dragged_line.pos().x())
        for frame_line in self.frame_lines.values():
            frame_line.setPos(frame_no)
        self.frame_line_dragged.emit(frame_no)

    def move_frame_line(self, x):
        for frame_line in self.frame_lines.values():
            frame_line.blockSignals(True)
            frame_line.setPos(x)
            frame_line.blockSignals(False)

    def set_frame_line_draggable(self, draggable):
        for frame_line in self.frame_lines.values():
            frame_line.setMovable(draggable)

    def set_frame_bound(self, bounds):
        for frame_line in self.frame_lines.values():
            frame_line.setBounds(bounds)

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
        self.frame_lines.clear()
        for name, p in self.plots.items():
            p.clear()
            self.frame_lines[name] = self.add_current_frame_line(p)

    def gui_save(self, settings):
        self.plot_splitter.gui_save(settings)

    def gui_restore(self, settings):
        self.plot_splitter.gui_restore(settings)


if __name__ == "__main__":
    import numpy as np

    sample_data = np.array(range(25))

    app = QtWidgets.QApplication([])
    widget = XYPlotWidget()
    widget.add_marker("test")
    widget.show()

    app.exec()
