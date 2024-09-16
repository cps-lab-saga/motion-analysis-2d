import pyqtgraph as pg
from qtpy import QtCore, QtGui


class LengthItem(pg.GraphicsObject):
    sigLineCornerMoved = QtCore.Signal(int, tuple)
    sigMoved = QtCore.Signal(object)

    def __init__(
        self,
        line_corners=((0, 0), (0, 1)),
        line_pen=None,
        line_hover_pen=None,
        handle_size=10,
        handle_pen=None,
        handle_hover_pen=None,
    ):
        pg.GraphicsObject.__init__(self)

        self.line_corners = list(line_corners)
        self.handle_size = handle_size

        self.handle_hover = [False] * 2
        self.handle_dragging = [False] * 2
        self.line_hover = False
        self.line_dragging = None

        self.picture = QtGui.QPicture()

        if line_pen is None:
            line_pen = pg.mkPen("w", width=2)
        self.line_pen = line_pen

        if line_hover_pen is None:
            line_hover_pen = pg.mkPen("b", width=3)
        self.line_hover_pen = line_hover_pen

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

        # line
        if self.line_hover:
            p.setPen(self.line_hover_pen)
        else:
            p.setPen(self.line_pen)
        p.drawLine(*[QtCore.QPointF(*a) for a in self.line_corners])

        # handles for line ends
        for point, hover in zip(self.line_corners, self.handle_hover):
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
        p.end()

    def paint(self, p, *args):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.generatePicture()
        p.drawPicture(0, 0, self.picture)

    def pos_at_handle(self, pos, size):
        handles = [False] * 2
        for i, point in enumerate(self.line_corners):
            d = (pos - QtCore.QPointF(*point)).manhattanLength()
            if d <= size * 2:
                handles[i] = True
                break
        return handles

    def hoverEvent(self, ev):
        self.line_hover = False

        if not ev.isExit():
            if any(self.handle_dragging) or self.line_dragging is not None:
                ev.acceptDrags(QtCore.Qt.LeftButton)
            else:
                (w, _), (_, h) = self.pixelVectors()
                local_handle_size = self.handle_size * w / 2
                self.handle_hover = self.pos_at_handle(ev.lastPos(), local_handle_size)
                if any(self.handle_hover):
                    self.update()
                    return

                self.line_hover = True
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
            elif self.line_hover:
                pos = ev.pos()
                self.line_dragging = [
                    QtCore.QPointF(*v) - pos for v in self.line_corners
                ]  # offsets

        elif ev.isFinish():
            self.handle_dragging = [False] * 4
            self.line_dragging = None

        if any(self.handle_dragging):
            i = self.handle_dragging.index(True)
            pos = ev.pos().toTuple()
            self.line_corners[i] = pos
            self.sigLineCornerMoved.emit(i, pos)
            self.update()
        elif self.line_dragging is not None:
            pos = ev.pos()
            self.line_corners = [(x + pos).toTuple() for x in self.line_dragging]
            self.sigMoved.emit(self.line_corners)
            self.update()

    def boundingRect(self):
        return QtCore.QRectF(self.picture.boundingRect())

    def setData(self, line_corners=None, outer_offsets=None):
        if line_corners is not None:
            self.line_corners = line_corners

    def setLineCorner(self, i, pos):
        self.line_corners[i] = pos

    def setLinePen(self, pen):
        self.line_pen = pen
        self.update()

    def setLineHoverPen(self, pen):
        self.line_hover_pen = pen
        self.update()

    def get_params(self):
        return self.line_corners


if __name__ == "__main__":
    item = LengthItem(line_corners=((0, 0), (0, 10)))
    plt = pg.plot()
    plt.addItem(item)
    plt.setAspectLocked()
    pg.exec()
