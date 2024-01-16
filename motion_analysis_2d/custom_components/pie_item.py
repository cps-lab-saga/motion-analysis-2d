import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui


class PieItem(pg.GraphicsObject):
    def __init__(
        self, center=(0, 0), radius=1, start_angle=0, span_angle=0, pen=None, brush=None
    ):
        pg.GraphicsObject.__init__(self)

        self.center = center
        self.radius = radius
        self.rect = QtCore.QRectF(0, 0, 1, 1)

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

        if self.getViewBox():
            (w, _), (_, h) = self.pixelVectors()
            local_radius = self.radius * w / 2
            self.rect = QtCore.QRectF(
                self.center[0] - local_radius,
                self.center[1] - local_radius,
                local_radius * 2,
                local_radius * 2,
            )
        p.drawPie(self.rect, self.start_angle, self.span_angle)
        p.end()

    def paint(self, p, *args):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.generatePicture()
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return self.rect

    def setData(self, start_angle, span_angle, center=None, radius=None):
        if center is not None and radius is not None:
            self.radius = radius
            self.center = center
        self.start_angle = round(start_angle) * 16
        self.span_angle = round(span_angle) * 16
        self.generatePicture()

    def setPen(self, pen):
        self.pen = pen
        self.update()

    def setBrush(self, brush):
        self.brush = brush
        self.update()


if __name__ == "__main__":
    item = PieItem((10, 10), 10, pen=pg.mkPen("w"), brush=pg.mkBrush("r"))
    plt = pg.plot()
    plt.setAspectLocked()
    plt.addItem(item)
    item.setData(100, 50, center=(10, 10), radius=10)
    pg.exec()
