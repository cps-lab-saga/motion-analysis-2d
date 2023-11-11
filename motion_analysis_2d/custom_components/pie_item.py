import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui


class PieItem(pg.GraphicsObject):
    def __init__(
        self, center=(0, 0), radius=1, start_angle=0, span_angle=0, pen=None, brush=None
    ):
        pg.GraphicsObject.__init__(self)
        diameter = radius * 2
        self.rect = QtCore.QRectF(
            center[0] - radius, center[1] - radius, diameter, diameter
        )

        self.start_angle = round(start_angle) * 16
        self.span_angle = round(span_angle) * 16
        self.picture = QtGui.QPicture()

        if pen is None:
            pen = pg.mkPen("w")
        self.pen = pen

        if brush is None:
            brush = pg.mkBrush("r")
        self.brush = brush

        self.generatePicture()

    def generatePicture(self):
        p = QtGui.QPainter(self.picture)
        p.setPen(self.pen)
        p.setBrush(self.brush)
        p.drawPie(self.rect, self.start_angle, self.span_angle)

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return self.rect

    def setData(self, start_angle, span_angle, center=None, radius=None):
        if center is not None and radius is not None:
            diameter = radius * 2
            self.rect = QtCore.QRectF(
                center[0] - radius, center[1] - radius, diameter, diameter
            )
        self.start_angle = round(start_angle) * 16
        self.span_angle = round(span_angle) * 16
        self.generatePicture()


if __name__ == "__main__":
    item = PieItem((10, 10), 10, pen=pg.mkPen("w"), brush=pg.mkBrush("r"))
    item.setData(100, 50)
    plt = pg.plot()
    plt.addItem(item)
    pg.exec()
