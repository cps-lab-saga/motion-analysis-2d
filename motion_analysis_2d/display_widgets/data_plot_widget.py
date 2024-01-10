import pyqtgraph as pg

from defs import QtWidgets, Signal
from motion_analysis_2d.custom_components import tab10_rgb
from motion_analysis_2d.display_widgets.plot_splitter import PlotSplitter


class DataPlotWidget(QtWidgets.QWidget):
    frame_line_dragged = Signal(int)

    def __init__(self, plots=("x", "y"), parent=None):
        super().__init__(parent=parent)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.plot_splitter = PlotSplitter(self)
        self.main_layout.addWidget(self.plot_splitter)

        self.foreground_color = self.palette().color(self.foregroundRole())
        self.frame_pen = pg.mkPen(color=tab10_rgb["purple"], width=1)
        self.frame_hover_pen = pg.mkPen(color=tab10_rgb["purple"], width=3)

        self.lines = {}
        self.plots = {}
        self.frame_lines = {}
        for i, v in enumerate(plots):
            self.add_plot(i, v)

    def add_plot(self, row, y_label, x_label=None):
        plot_widget = self.plot_splitter.add_plot(row=row)
        if row > 0:
            plot_widget.setXLink(self.plot_splitter[0])

        plot_widget.setLabel("left", y_label)
        if x_label is not None:
            plot_widget.setLabel("bottom", x_label)
        plot_widget.getAxis("left").setWidth(60)
        legend = plot_widget.addLegend(offset=(-1, 1))
        # legend.setColumnCount(2)

        plot_widget.setMenuEnabled(False)
        plot_widget.autoBtn.clicked.disconnect()
        plot_widget.autoBtn.clicked.connect(self.auto_range)
        plot_widget.setMouseEnabled(x=True, y=True)

        self.plots[y_label] = plot_widget
        self.frame_lines[y_label] = self.add_current_frame_line(plot_widget)
        self.lines[y_label] = {}

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

    def add_line(self, param, label, color=None, show_in_legend=False):
        plot_widget = self.plots[param]

        if color is None:
            color = self.foreground_color
        if show_in_legend:
            line = plot_widget.plot(pen=color, name=label)
        else:
            line = plot_widget.plot(pen=color)

        self.lines[param][label] = (line, True)
        return line

    def show_line(self, param, label):
        line, show = self.lines[param][label]
        if show:
            return
        else:
            self.plots[param].addItem(line)
            self.lines[param][label] = (line, True)

    def hide_line(self, param, label):
        line, show = self.lines[param][label]
        if not show:
            return
        else:
            self.plots[param].removeItem(line)
            self.lines[param][label] = (line, False)

    def remove_line(self, param, label):
        line, show = self.lines[param].pop(label, None)
        if show:
            self.plots[param].removeItem(line)

    def update_line(self, param, label, y, x=None):
        if x is None:
            self.lines[param][label][0].setData(y)
        else:
            self.lines[param][label][0].setData(x, y)

    def auto_range(self):
        plot_item = self.sender().parentItem()
        plot_item.enableAutoRange()

    def clear(self):
        self.lines.clear()
        self.frame_lines.clear()
        for name, p in self.plots.items():
            p.clear()
            self.lines[name] = {}
            self.frame_lines[name] = self.add_current_frame_line(p)

    def gui_save(self, settings):
        self.plot_splitter.gui_save(settings)

    def gui_restore(self, settings):
        self.plot_splitter.gui_restore(settings)


if __name__ == "__main__":
    import numpy as np

    sample_data = np.array(range(25))

    app = QtWidgets.QApplication([])
    widget = DataPlotWidget(("x", "y"))
    widget.add_line("y", "test")
    widget.show()

    app.exec()
