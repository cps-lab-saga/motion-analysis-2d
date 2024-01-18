import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

from motion_analysis_2d.funcs.geometric_calc import (
    make_offset_polygon,
    distance_from_line,
)


class PerspectiveItem(pg.GraphicsObject):
    sigInnerCornerMoved = QtCore.Signal(int, tuple)
    sigMoved = QtCore.Signal(object)

    def __init__(
        self,
        inner_corners=((0, 0), (0, 1), (1, 1), (1, 0)),
        outer_offsets=(1, 0.5, 1, 1),
        handle_size=10,
        inner_pen=None,
        inner_hover_pen=None,
        outer_pen=None,
        outer_hover_pen=None,
        handle_pen=None,
        handle_hover_pen=None,
    ):
        pg.GraphicsObject.__init__(self)

        self.inner_corners = list(inner_corners)
        self.outer_offsets = list(outer_offsets)
        self.handle_size = handle_size
        self.outer_corners = list(inner_corners)

        self.handle_hover = [False] * 4
        self.handle_dragging = [False] * 4
        self.inner_hover = False
        self.inner_dragging = None
        self.outer_hover = [False] * 4
        self.outer_dragging = None

        self.picture = QtGui.QPicture()

        if inner_pen is None:
            inner_pen = pg.mkPen("w", width=2)
        self.inner_pen = inner_pen

        if inner_hover_pen is None:
            inner_hover_pen = pg.mkPen("b", width=3)
        self.inner_hover_pen = inner_hover_pen

        if outer_pen is None:
            outer_pen = pg.mkPen("w", width=1)
        self.outer_pen = outer_pen

        if outer_hover_pen is None:
            outer_hover_pen = pg.mkPen("b", width=3)
        self.outer_hover_pen = outer_hover_pen

        if handle_pen is None:
            handle_pen = pg.mkPen((150, 255, 255), width=1)
        self.handle_pen = handle_pen

        if handle_hover_pen is None:
            handle_hover_pen = pg.mkPen((150, 255, 255), width=3)
        self.handle_hover_pen = handle_hover_pen

    def generatePicture(self):
        if not self.getViewBox():
            return

        p = QtGui.QPainter(self.picture)
        (w, _), (_, h) = self.pixelVectors()
        local_handle_size = self.handle_size * w / 2

        # inner box
        if self.inner_hover:
            p.setPen(self.inner_hover_pen)
        else:
            p.setPen(self.inner_pen)
        p.drawPolygon([QtCore.QPointF(*a) for a in self.inner_corners])

        # handles for inner box
        for point, hover in zip(self.inner_corners, self.handle_hover):
            if hover:
                p.setPen(self.handle_hover_pen)
            else:
                p.setPen(self.handle_pen)
            p.drawEllipse(
                QtCore.QRectF(
                    point[0] - local_handle_size,
                    point[1] - local_handle_size,
                    local_handle_size * 2,
                    local_handle_size * 2,
                )
            )

        # outer box
        outer_points = make_offset_polygon(self.inner_corners, self.outer_offsets)
        for i, hover in enumerate(self.outer_hover):
            if hover:
                p.setPen(self.outer_hover_pen)
            else:
                p.setPen(self.outer_pen)
            p.drawLine(
                QtCore.QPointF(*outer_points[i]),
                QtCore.QPointF(*outer_points[(i + 1) % 4]),
            )
        self.outer_corners = outer_points
        p.end()

    def paint(self, p, *args):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.generatePicture()
        p.drawPicture(0, 0, self.picture)

    def pos_at_handle(self, pos, size):
        handles = [False] * 4
        for i, point in enumerate(self.inner_corners):
            d = (pos - QtCore.QPointF(*point)).manhattanLength()
            if d <= size * 2:
                handles[i] = True
                break
        return handles

    def pos_at_outer(self, pos, size):
        outer = [False] * 4
        for i, point in enumerate(self.outer_corners):
            next_i = (i + 1) % 4
            d = distance_from_line(
                pos.toTuple(),
                self.outer_corners[i],
                self.outer_corners[next_i],
                clip=True,
            )
            if d <= size:
                outer[i] = True
                break
        return outer

    def hoverEvent(self, ev):
        self.inner_hover = False

        if not ev.isExit():
            if (
                any(self.handle_dragging)
                or self.inner_dragging is not None
                or self.outer_dragging is not None
            ):
                ev.acceptDrags(QtCore.Qt.LeftButton)
            else:
                (w, _), (_, h) = self.pixelVectors()
                local_handle_size = self.handle_size * w / 2
                self.handle_hover = self.pos_at_handle(ev.lastPos(), local_handle_size)
                if any(self.handle_hover):
                    self.update()
                    return

                self.outer_hover = self.pos_at_outer(ev.lastPos(), 20 * w / 2)
                if any(self.outer_hover):
                    self.update()
                    return

                rect = QtCore.QRectF(
                    QtCore.QPointF(*self.inner_corners[0]),
                    QtCore.QPointF(*self.inner_corners[2]),
                )
                if rect.contains(ev.pos()):
                    self.inner_hover = True
                    self.update()
                    return
        else:
            self.update()

    def mouseDragEvent(self, ev):
        if ev.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        ev.accept()
        if ev.isStart() and ev.button() == QtCore.Qt.MouseButton.LeftButton:
            if any(self.handle_hover):
                self.handle_dragging = self.handle_hover
            elif any(self.outer_hover):
                i = self.outer_hover.index(True)
                next_i = (i + 1) % 4
                self.outer_dragging = (
                    i,
                    self.inner_corners[i],
                    self.inner_corners[next_i],
                )
            elif self.inner_hover:
                pos = ev.pos()
                self.inner_dragging = [
                    QtCore.QPointF(*v) - pos for v in self.inner_corners
                ]  # offsets

        elif ev.isFinish():
            self.handle_dragging = [False] * 4
            self.inner_dragging = None
            self.outer_dragging = None

        if any(self.handle_dragging):
            i = self.handle_dragging.index(True)
            pos = ev.pos().toTuple()
            self.inner_corners[i] = pos
            self.sigInnerCornerMoved.emit(i, pos)
            self.update()
        elif self.outer_dragging is not None:
            pos = ev.pos()
            i, line_start, line_end = self.outer_dragging
            d = distance_from_line(pos.toTuple(), line_start, line_end)
            self.outer_offsets[i] = d
            self.update()

        elif self.inner_dragging is not None:
            pos = ev.pos()
            self.inner_corners = [(x + pos).toTuple() for x in self.inner_dragging]
            self.sigMoved.emit(self.inner_corners)
            self.update()

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def setData(self, inner_corners=None, outer_offsets=None):
        if inner_corners is not None:
            self.inner_corners = inner_corners
        if outer_offsets is not None:
            self.outer_offsets = outer_offsets

    def setInnerCorner(self, i, pos):
        self.inner_corners[i] = pos

    def setInnerPen(self, pen):
        self.inner_pen = pen
        self.update()

    def setOuterPen(self, pen):
        self.outer_pen = pen
        self.update()

    def setInnerHoverPen(self, pen):
        self.inner_hover_pen = pen
        self.update()

    def setOuterHoverPen(self, pen):
        self.outer_hover_pen = pen
        self.update()

    def get_params(self):
        return {
            "inner_corners": self.inner_corners,
            "outer_corners": self.outer_corners,
            "outer_offsets": self.outer_offsets,
        }


if __name__ == "__main__":
    item = PerspectiveItem(inner_corners=((0, 0), (0, 10), (10, 10), (10, 0)))
    plt = pg.plot()
    plt.addItem(item)
    plt.setAspectLocked()
    pg.exec()
