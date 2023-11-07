import contextlib
from enum import Enum
from pathlib import Path

import cv2 as cv
import pyqtgraph as pg

from defs import QtCore, QtWidgets, Signal
from motion_analysis_2d.custom_components import tab10_rgb
from motion_analysis_2d.funcs import is_json_file, prevent_name_collision


class FrameWidget(QtWidgets.QWidget):
    new_tracker_suggested = Signal(tuple, tuple, tuple)
    tracker_added = Signal(str, tuple, tuple, tuple, tuple, str)
    tracker_moved = Signal(str, tuple, tuple, tuple, tuple, str)
    tracker_removed = Signal(str)
    marker_file_dropped = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setAcceptDrops(True)

        pg.setConfigOptions(
            background=None,
            foreground=self.palette().color(self.foregroundRole()),
            antialias=True,
        )

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.show_crosshairs = False
        self.mouse_mode = MouseModes.NORMAL
        self.add_tracker_steps = AddTrackerSteps.SELECT_BBOX_POINT1

        self.traj_len = 30
        self.frame_label_text_color = (255, 255, 255)
        self.frame_label_fill_color = (0, 0, 0, 150)
        self.roi_label_fill_color = (0, 0, 0, 150)

        self.transparent_pen = pg.mkPen(color=(0, 0, 0, 0), width=0)
        self.new_roi_pen = pg.mkPen(color=tab10_rgb["green"], width=3)
        self.trajectory_pen = pg.mkPen(color=tab10_rgb["green"], width=3)
        self.crosshair_pen = pg.mkPen(color=tab10_rgb["cyan"], width=1)

        self.trackers = {
            "name": [],
            "roi": [],
            "label": [],
            "target": [],
            "traj": [],
            "offset": [],
            "color": [],
            "tracker_type": [],
        }

        self.plot_widget = pg.PlotWidget()
        self.fig = self.plot_widget.getPlotItem()
        self.main_layout.addWidget(self.plot_widget)

        self.im_item = pg.ImageItem(axisOrder="row-major")

        self.fig.addItem(self.im_item)
        self.fig.setAspectLocked()
        self.fig.invertY(True)
        self.fig.setMenuEnabled(False)
        self.fig.setLabel("left", "Pixels")
        self.fig.setLabel("bottom", "Pixels")
        self.fig.hideAxis("left")
        self.fig.hideAxis("bottom")
        self.frame_label = self.add_frame_label()

        self.v_crosshair = pg.InfiniteLine(
            pos=pg.Point(-1000, -1000), angle=90, movable=False, pen=self.crosshair_pen
        )
        self.v_crosshair_label = pg.TextItem(
            "", anchor=(0, 1), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )
        self.h_crosshair = pg.InfiniteLine(
            pos=pg.Point(-1000, -1000), angle=0, movable=False, pen=self.crosshair_pen
        )
        self.h_crosshair_label = pg.TextItem(
            "", anchor=(0, 1), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )
        self.intensity_crosshair_label = pg.TextItem(
            "", anchor=(1, 0), color=self.crosshair_pen.color(), fill=(0, 0, 0)
        )

        self.img = None
        self.dropped_img = None
        self.temp_tracker = None

        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.mouse_moved)
        self.plot_widget.sigRangeChanged.connect(self.range_changed)

    def mouse_clicked(self, evt):
        if self.mouse_mode == MouseModes.ADD_TRACKER:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                if self.add_tracker_steps == AddTrackerSteps.SELECT_BBOX_POINT1:
                    self.start_new_tracker(evt.scenePos())
                elif self.add_tracker_steps == AddTrackerSteps.SELECT_BBOX_POINT2:
                    self.finish_new_tracker(evt.scenePos())
                elif self.add_tracker_steps.SELECT_OFFSET:
                    self.select_tracker_target(evt.scenePos())
        elif self.mouse_mode == MouseModes.REMOVE_TRACKER:
            if not evt.double() and evt.button() == QtCore.Qt.LeftButton:
                pos = evt.scenePos()
                items = self.fig.scene().items(pos)
                for item in items:
                    if isinstance(item, (pg.ROI, pg.TargetItem)):
                        self.remove_tracker(item)
                        break

        # Double right click to toggle crosshairs
        if evt.double() and evt.button() == QtCore.Qt.RightButton:
            self.toggle_crosshairs(evt)

    def mouse_moved(self, pos):
        if self.mouse_mode == MouseModes.ADD_TRACKER:
            if self.add_tracker_steps == AddTrackerSteps.SELECT_BBOX_POINT2:
                self.shape_new_tracker(pos)

        self.animate_crosshairs(pos)

    def range_changed(self):
        self.adjust_crosshairs()

    def set_image(self, img):
        if img is None:
            return

        self.img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        self.im_item.setImage(self.img)

    def update_frame(self, img, frame_no, t_sec):
        self.set_image(img)
        self.update_frame_label(frame_no, t_sec)

    def add_frame_label(self):
        frame_label = pg.TextItem(
            "Frame: {}\nTime: {:.2f} s".format(0, 0),
            anchor=(0, 0),
            color=self.frame_label_text_color,
            fill=self.frame_label_fill_color,
        )
        frame_label.setParentItem(self.fig.getViewBox())
        return frame_label

    def update_frame_label(self, frame_no, time, fps=None):
        if fps is None:
            self.frame_label.setText(f"Frame: {frame_no}\n" f"Time: {time:.2f} s")
        else:
            self.frame_label.setText(
                f"Frame: {frame_no}\n" f"Time: {time:.2f} s\n" f"FPS: {fps:.0f}\n"
            )

    def set_mouse_mode(self, mode):
        if isinstance(mode, str):
            mode = MouseModes[mode.upper()]
        if mode == MouseModes.NORMAL:
            self.plot_widget.setCursor(QtCore.Qt.ArrowCursor)
        else:
            self.plot_widget.setCursor(QtCore.Qt.CrossCursor)
        self.mouse_mode = mode

    def start_new_tracker(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        x, y = self.keep_point_in_frame(x, y)
        new_roi = pg.ROI(
            (x, y),
            size=(0, 0),
            pen=self.new_roi_pen,
            movable=False,
            resizable=False,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )

        # default (centre of bounding box)
        target_x, target_y = [round(a) for a in self.calc_centre_roi(new_roi)]
        target = pg.TargetItem(
            (target_x, target_y),
            size=10,
            pen=self.transparent_pen,
            brush=self.transparent_pen.color(),
            movable=False,
        )

        self.temp_tracker = {"roi": new_roi, "target": target}
        self.fig.addItem(self.temp_tracker["roi"])
        self.fig.addItem(self.temp_tracker["target"])

        # move to next step
        if self.add_tracker_steps.is_last():
            self.emit_new_tracker_suggestion()
        else:
            self.add_tracker_steps = self.add_tracker_steps.next()

    def shape_new_tracker(self, pos):
        roi_x, roi_y = self.temp_tracker["roi"].pos()
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x, y = self.keep_point_in_frame(mouse_point.x(), mouse_point.y())

        w = round(x) - roi_x
        h = round(y) - roi_y
        self.temp_tracker["roi"].setSize((w, h))

        # default (centre of bounding box)
        target_x, target_y = [
            round(a) for a in self.calc_centre_roi(self.temp_tracker["roi"])
        ]
        self.temp_tracker["target"].setPos((target_x, target_y))

    def finish_new_tracker(self, pos):
        x, y = self.temp_tracker["roi"].pos()
        w, h = self.temp_tracker["roi"].size()

        # make roi size positive (origin at bottom left)
        if w < 0:
            x = round(x + w)
            w = round(abs(w))
        if h < 0:
            y = round(y + h)
            h = round(abs(h))
        self.temp_tracker["roi"].setPos((x, y))
        self.temp_tracker["roi"].setSize((w, h))

        # default (centre of bounding box)
        target_x, target_y = [
            round(a) for a in self.calc_centre_roi(self.temp_tracker["roi"])
        ]
        self.temp_tracker["target"].setPos((target_x, target_y))

        # move to next step
        if self.add_tracker_steps.is_last():
            self.emit_new_tracker_suggestion()
        else:
            self.add_tracker_steps = self.add_tracker_steps.next()

    def select_tracker_target(self, pos):
        mouse_point = self.fig.vb.mapSceneToView(pos)
        x = round(mouse_point.x())
        y = round(mouse_point.y())
        self.temp_tracker["target"].setPos((x, y))
        self.temp_tracker["target"].setPen(self.new_roi_pen)

        # move to next step
        if self.add_tracker_steps.is_last():
            self.emit_new_tracker_suggestion()
            self.add_tracker_steps = self.add_tracker_steps.first()
        else:
            self.add_tracker_steps = self.add_tracker_steps.next()

    def emit_new_tracker_suggestion(self):
        if self.temp_tracker is None:
            return

        x, y = (round(a) for a in self.temp_tracker["roi"].pos())
        w, h = (round(a) for a in self.temp_tracker["roi"].size())

        offset_x, offset_y = [
            round(a)
            for a in (
                self.temp_tracker["target"].pos()
                - self.calc_centre_roi(self.temp_tracker["roi"])
            )
        ]  # from centre of roi

        self.new_tracker_suggested.emit(
            (x, y),
            (w, h),
            (offset_x, offset_y),
        )

    @staticmethod
    def calc_centre_roi(roi):
        return roi.pos() + roi.size() / 2

    def remove_temp_tracker(self):
        if self.temp_tracker is not None:
            self.fig.removeItem(self.temp_tracker["roi"])
            self.fig.removeItem(self.temp_tracker["target"])
            self.temp_tracker = None

    def add_tracker(self, name, bbox_pos, bbox_size, offset, color, tracker_type):
        name = self.prevent_name_collision(name)
        pen = pg.mkPen(color=color, width=2)
        hover_pen = pg.mkPen(color=color, width=4)

        roi = pg.ROI(
            bbox_pos,
            size=bbox_size,
            pen=pen,
            hoverPen=hover_pen,
            movable=True,
            resizable=True,
            rotatable=False,
            rotateSnap=False,
            scaleSnap=False,
        )
        roi.addScaleHandle([0, 0], [0.5, 0.5])
        roi.sigRegionChanged.connect(self.bbox_moved)
        roi.setZValue(0)
        self.fig.addItem(roi)

        cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
        target_pos = cx + offset[0], cy + offset[1]
        target = pg.TargetItem(
            target_pos,
            size=10,
            pen=pen,
            hoverPen=hover_pen,
            movable=True,
        )
        target.sigPositionChanged.connect(self.target_moved)
        target.setZValue(1)
        self.fig.addItem(target)

        label = pg.TargetLabel(
            target,
            name,
            anchor=(0, 1),
            color=pen.color(),
            fill=self.roi_label_fill_color,
        )

        traj = self.fig.plot(pen=pen)

        self.trackers["name"].append(name)
        self.trackers["roi"].append(roi)
        self.trackers["target"].append(target)
        self.trackers["label"].append(label)
        self.trackers["traj"].append(traj)
        self.trackers["offset"].append(offset)
        self.trackers["color"].append(color)
        self.trackers["tracker_type"].append(tracker_type)

        self.tracker_added.emit(name, bbox_pos, bbox_size, offset, color, tracker_type)

    def remove_tracker(self, item):
        if isinstance(item, pg.ROI):
            i = self.trackers["roi"].index(item)
        elif isinstance(item, pg.TargetItem):
            i = self.trackers["target"].index(item)
        else:
            raise TypeError("Unrecognized item type")

        name = self.trackers["name"][i]
        self.fig.removeItem(self.trackers["roi"][i])
        self.fig.removeItem(self.trackers["target"][i])
        self.fig.removeItem(self.trackers["traj"][i])

        for item in self.trackers.values():
            item.pop(i)

        self.tracker_removed.emit(name)

    def prevent_name_collision(self, name):
        return prevent_name_collision(name, self.trackers["name"])

    def frame_shape_changed(self):
        for roi in self.trackers["roi"]:
            self.keep_roi_in_frame(roi)

    def bbox_moved(self, roi=None):
        if roi is None:
            roi = self.sender()
        self.keep_roi_in_frame(roi)

        i = self.trackers["roi"].index(roi)
        name = self.trackers["name"][i]
        target = self.trackers["target"][i]
        offset = self.trackers["offset"][i]
        bbox_pos = [round(a) for a in roi.pos()]
        bbox_size = [round(a) for a in roi.size()]
        tracker_type = self.trackers["tracker_type"][i]
        color = self.trackers["color"][i]

        cx, cy = [round(a) for a in self.calc_centre_roi(roi)]
        target_pos = cx + offset[0], cy + offset[1]
        target.setPos(target_pos)

        self.tracker_moved.emit(name, bbox_pos, bbox_size, offset, color, tracker_type)

    def target_moved(self):
        target = self.sender()

        i = self.trackers["target"].index(target)
        name = self.trackers["name"][i]
        roi = self.trackers["roi"][i]
        bbox_pos = [round(a) for a in roi.pos()]
        bbox_size = [round(a) for a in roi.size()]
        offset = [round(a) for a in target.pos() - self.calc_centre_roi(roi)]
        tracker_type = self.trackers["tracker_type"][i]
        color = self.trackers["color"][i]
        self.trackers["offset"][i] = offset

        self.tracker_moved.emit(name, bbox_pos, bbox_size, offset, color, tracker_type)

    def clear(self):
        for l in self.trackers.values():
            l.clear()

        self.fig.clear()
        self.im_item = pg.ImageItem(axisOrder="row-major")
        self.fig.addItem(self.im_item)

    def keep_roi_in_frame(self, roi):
        roi_x, roi_y = roi.pos()
        roi_w, roi_h = roi.size()
        im_x, im_y = self.im_item.pos()
        im_w, im_h = self.im_item.width(), self.im_item.height()

        if roi_w > im_w:
            roi_w = im_w
        if roi_h > im_h:
            roi_h = im_h
        if roi_w <= 0:
            roi_w = 1
        if roi_h <= 0:
            roi_h = 1

        if roi_x < im_x:
            roi_x = im_x
        elif roi_x + roi_w > im_x + im_w:
            roi_x = im_x + im_w - roi_w
        if roi_y < im_y:
            roi_y = im_y
        elif roi_y + roi_h > im_y + im_h:
            roi_y = im_y + im_h - roi_h

        roi.blockSignals(True)
        roi.setPos((roi_x, roi_y))
        roi.setSize((roi_w, roi_h))
        roi.blockSignals(False)

    def keep_point_in_frame(self, x, y):
        im_x, im_y = self.im_item.pos()
        im_w, im_h = self.im_item.width(), self.im_item.height()

        if x > im_x + im_w:
            x = im_x + im_w
        elif x < im_x:
            x = im_x
        if y > im_y + im_h:
            y = im_y + im_h
        elif y < im_y:
            y = im_y

        return x, y

    def move_tracker(self, name, bbox, target_pos):
        i = self.trackers["name"].index(name)
        roi = self.trackers["roi"][i]
        target = self.trackers["target"][i]

        bbox_pos = bbox[:2]
        bbox_size = bbox[2:]
        roi.blockSignals(True)
        roi.setPos(bbox_pos)
        roi.setSize(bbox_size)
        roi.blockSignals(False)

        target.setPos(target_pos)
        self.trackers["offset"][i] = [
            round(a) for a in target.pos() - self.calc_centre_roi(roi)
        ]

    def hide_tracker(self, name):
        i = self.trackers["name"].index(name)
        roi = self.trackers["roi"][i]
        target = self.trackers["target"][i]

        roi.blockSignals(True)
        target.blockSignals(True)
        roi.setPos((0, 0))
        target.setPos((0, 0))
        roi.blockSignals(False)
        target.blockSignals(False)

    def show_trajectory(self, name, frame_no, target):
        i = self.trackers["name"].index(name)
        traj = self.trackers["traj"][i]
        if frame_no > self.traj_len:
            traj.setData(
                target[frame_no - self.traj_len : frame_no, 0],
                target[frame_no - self.traj_len : frame_no, 1],
            )
        else:
            traj.setData(target[:frame_no, 0], target[:frame_no, 1])

    def animate_crosshairs(self, pos):
        """
        animate crosshairs and display x and y values
        """
        if not self.fig.sceneBoundingRect().contains(pos) or not self.show_crosshairs:
            return
        with contextlib.suppress(Exception):
            mouse_point = self.fig.vb.mapSceneToView(pos)
            x = round(mouse_point.x())
            y = round(mouse_point.y())
            intensity = self.img[y, x]

            self.v_crosshair.setPos(x)
            self.h_crosshair.setPos(y)

            xlim, ylim = self.fig.viewRange()
            self.v_crosshair_label.setText(str(x))
            self.v_crosshair_label.setPos(x, ylim[1])
            self.h_crosshair_label.setText(str(y))
            self.h_crosshair_label.setPos(xlim[0], y)
            self.intensity_crosshair_label.setText(str(intensity))
            self.intensity_crosshair_label.setPos(xlim[1], ylim[0])

    def toggle_crosshairs(self, evt):
        if self.show_crosshairs:
            self.show_crosshairs = False
            self.fig.removeItem(self.v_crosshair)
            self.fig.removeItem(self.v_crosshair_label)
            self.fig.removeItem(self.h_crosshair)
            self.fig.removeItem(self.h_crosshair_label)
            self.fig.removeItem(self.intensity_crosshair_label)
        else:
            self.show_crosshairs = True
            self.fig.addItem(self.v_crosshair, ignoreBounds=True)
            self.fig.addItem(self.v_crosshair_label, ignoreBounds=True)
            self.fig.addItem(self.h_crosshair, ignoreBounds=True)
            self.fig.addItem(self.h_crosshair_label, ignoreBounds=True)
            self.fig.addItem(self.intensity_crosshair_label, ignoreBounds=True)
            self.mouse_moved(evt.scenePos())

    def adjust_crosshairs(self):
        """
        Move crosshair labels if resized.
        """
        if self.show_crosshairs:
            xlim, ylim = self.fig.viewRange()
            self.v_crosshair_label.setPos(self.v_crosshair_label.pos().x(), ylim[1])
            self.h_crosshair_label.setPos(xlim[0], self.h_crosshair_label.pos().y())
            self.intensity_crosshair_label.setPos(xlim[1], ylim[0])

    def update_vis(self, markers_data):
        self.update_marker_vis(markers_data)
        self.update_traj_vis(markers_data)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            if is_json_file(e.mimeData().urls()[0].toLocalFile()):
                e.acceptProposedAction()
                e.setDropAction(QtCore.Qt.CopyAction)
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            if is_json_file(e.mimeData().urls()[0].toLocalFile()):
                e.setDropAction(QtCore.Qt.CopyAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(QtCore.Qt.CopyAction)
            path = Path(e.mimeData().urls()[0].toLocalFile())
            if is_json_file(path):
                e.accept()
                self.marker_file_dropped.emit(path)
        else:
            super().dropEvent(e)


class MouseModes(Enum):
    NORMAL = 0
    ADD_TRACKER = 1
    REMOVE_TRACKER = 2


class AddTrackerSteps(Enum):
    SELECT_BBOX_POINT1 = 1
    SELECT_BBOX_POINT2 = 2
    SELECT_OFFSET = 3

    def next(self):
        members = list(self.__class__)
        index = members.index(self) + 1
        if index >= len(members):
            index = 0
        return members[index]

    def first(self):
        members = list(self.__class__)
        return members[0]

    def is_last(self):
        members = list(self.__class__)
        index = members.index(self)
        if index >= len(members) - 1:
            return True
        else:
            return False


if __name__ == "__main__":
    import numpy as np

    black_img = np.zeros([100, 100, 3], dtype=np.uint8)

    app = QtWidgets.QApplication([])
    widget = FrameWidget()
    widget.set_image(black_img)
    widget.set_mouse_mode("add_tracker")
    # widget.add_tracker("test", (20, 20), (20, 20), (20, 20), "green", "")
    widget.show()

    app.exec()
