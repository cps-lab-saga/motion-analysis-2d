import pyqtgraph as pg

from defs import QtWidgets, QtCore


class PlotSplitter(QtWidgets.QSplitter):
    def __init__(self, parent=None):
        super().__init__(QtCore.Qt.Vertical, parent=parent)

        self.save_heading = "Plot"
        self.setChildrenCollapsible(True)
        pg.setConfigOptions(
            background=None,
            foreground=self.palette().color(self.foregroundRole()),
            antialias=True,
        )

    def add_plot(self, row):
        plot_widget = pg.PlotWidget()
        self.insertWidget(row, plot_widget)
        return plot_widget.getPlotItem()

    def __getitem__(self, i):
        if plot_widget := self.widget(i):
            return plot_widget.getPlotItem()

    def gui_save(self, settings):
        settings.setValue("/".join([self.save_heading, "state"]), self.saveState())

    def gui_restore(self, settings):
        val = settings.value("/".join([self.save_heading, "state"]))
        self.restoreState(val)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.processEvents()

    app.exec()
