import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui


class ArrowItem(pg.GraphicsObject):
    def __init__(
        self,
        start_pos=(0, 0),
        end_pos=(100, 0),
        arrow_width=8,
        arrow_height=8,
        stem_pen=None,
        arrow_pen=None,
        arrow_brush=None,
    ):
        pg.GraphicsObject.__init__(self)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.arrow_width = arrow_width
        self.arrow_height = arrow_height
        self.picture = QtGui.QPicture()

        if stem_pen is None:
            stem_pen = pg.mkPen("w", width=4)
        self.stem_pen = stem_pen

        if arrow_pen is None:
            arrow_pen = pg.mkPen(None)
        self.arrow_pen = arrow_pen

        if arrow_brush is None:
            arrow_brush = pg.mkBrush("r")
        self.arrow_brush = arrow_brush

        self.generatePicture()

    def generatePicture(self):
        p = QtGui.QPainter(self.picture)
        start_point = QtCore.QPointF(*self.start_pos)
        end_point = QtCore.QPointF(*self.end_pos)

        vec = end_point - start_point
        unit_vec = vec / vec.manhattanLength()
        perpendicular_unit_vec = QtCore.QPointF(unit_vec.y(), -unit_vec.x())

        p.setPen(self.stem_pen)
        p.drawLine(
            start_point + unit_vec * self.arrow_height,
            end_point - unit_vec * self.arrow_height,
        )

        p.setPen(self.arrow_pen)
        p.setBrush(self.arrow_brush)

        # end arrow
        p.drawPolygon(
            [
                end_point,
                end_point
                - unit_vec * self.arrow_height
                - perpendicular_unit_vec * self.arrow_width / 2,
                end_point
                - unit_vec * self.arrow_height
                + perpendicular_unit_vec * self.arrow_width / 2,
            ],
        )

        # start arrow
        p.drawPolygon(
            [
                start_point,
                start_point
                + unit_vec * self.arrow_height
                - perpendicular_unit_vec * self.arrow_width / 2,
                start_point
                + unit_vec * self.arrow_height
                + perpendicular_unit_vec * self.arrow_width / 2,
            ],
        )

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def setData(
        self,
        start_pos,
        end_pos,
        stem_pen=None,
        arrow_width=None,
        arrow_height=None,
    ):
        if stem_pen is not None:
            self.stem_pen = stem_pen
        if arrow_width is not None:
            self.arrow_width = arrow_width
        if arrow_height is not None:
            self.arrow_height = arrow_height
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.generatePicture()

    def setStemPen(self, pen):
        self.stem_pen = pen

    def setArrowPen(self, pen):
        self.arrow_pen = pen

    def setArrowBrush(self, brush):
        self.arrowBrush = brush


if __name__ == "__main__":
    item = ArrowItem(stem_pen=pg.mkPen("w", width=4), arrow_brush=pg.mkBrush("r"))
    item.setData((0, 0), (100, 100))
    plt = pg.plot()
    plt.setAspectLocked()
    plt.addItem(item)
    pg.exec()
