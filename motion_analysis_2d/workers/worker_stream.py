from time import sleep

import cv2 as cv

from motion_analysis_2d.defs import QtCore, Signal
from motion_analysis_2d.funcs import (
    undistort_map,
)


class StreamWorker(QtCore.QObject):
    stream_props = Signal(tuple, float, int)
    finished = Signal()
    progress = Signal()

    def __init__(
        self,
        path,
        stream_queue,
        *args,
        **kwargs,
    ):
        super().__init__()

        self.path = path
        self.stream_queue = stream_queue
        self.cap = None

        self.intrinsic_prop = None
        self.orient_prop = ("no_flip", "0")
        self.extrinsic_prop = None

        self.frame_no = 0
        self.timestamp = 0
        self.frame_rate = 0
        self.no_of_frames = 0
        self.frame_shape = (0, 0)

        self.frame = None

        self.stop_flag = False
        self.play_flag = False
        self.track_flag = False
        self.mutex = QtCore.QMutex()

    def stream(self):
        self.stop_flag = False
        self.cap = cv.VideoCapture(str(self.path))

        self.frame_shape = (
            int(self.cap.get(cv.CAP_PROP_FRAME_HEIGHT)),
            int(self.cap.get(cv.CAP_PROP_FRAME_WIDTH)),
        )
        self.frame_rate = self.cap.get(cv.CAP_PROP_FPS)
        self.no_of_frames = int(self.cap.get(cv.CAP_PROP_FRAME_COUNT))
        self.stream_props.emit(self.frame_shape, self.frame_rate, self.no_of_frames)

        self.read_single_frame()
        self.cap.set(cv.CAP_PROP_POS_FRAMES, 0)

        while not self.stop_flag:
            if self.play_flag:
                self.read_single_frame()
            else:
                sleep(0.3)

        self.cap.release()
        self.finished.emit()
        self.stop_flag = False
        self.deleteLater()

    def read_single_frame(self, track=None):
        if track is None:
            track = self.track_flag

        ret, frame = self.cap.read()
        if not ret:
            return

        self.mutex.lock()
        self.frame_no = int(self.cap.get(cv.CAP_PROP_POS_FRAMES))
        self.timestamp = self.cap.get(cv.CAP_PROP_POS_MSEC)
        self.frame = self.process_frame(frame)

        self.stream_queue.put(
            (
                self.frame_no,
                self.timestamp,
                self.frame,
                track,
            )
        )
        self.mutex.unlock()
        return (
            self.frame_no,
            self.timestamp,
            self.frame,
        )

    def process_frame(self, frame):
        frame = self.undistort(frame)
        frame = self.reorient(frame)
        frame = self.change_perspective(frame)
        return frame

    def move_frame_forwards(self, track=None):
        return self.read_single_frame(track=track)

    def move_frame_backwards(self, track=None):
        self.cap.set(cv.CAP_PROP_POS_FRAMES, self.frame_no - 2)
        return self.read_single_frame(track=track)

    def read_current_frame(self, track=None):
        self.cap.set(cv.CAP_PROP_POS_FRAMES, self.frame_no - 1)
        return self.read_single_frame(track=track)

    def move_frame_to(self, frame_no, track=False):
        self.cap.set(cv.CAP_PROP_POS_FRAMES, frame_no - 1)
        return self.read_single_frame(track=track)

    def set_stop(self):
        self.stop_flag = True

    def set_play(self):
        self.play_flag = True

    def set_pause(self):
        self.play_flag = False

    def set_tracking(self, track):
        self.track_flag = track

    def undistort(self, frame):
        if self.intrinsic_prop is not None:
            return undistort_map(frame, *self.intrinsic_prop)
        else:
            return frame

    def reorient(self, frame):
        if self.orient_prop is not None:
            return self.flip_img(self.rotate_img(frame))
        else:
            return frame

    def flip_img(self, frame):
        setting = self.orient_prop[0]
        if setting == "no_flip":
            return frame
        elif setting == "h_flip":
            return cv.flip(frame, 1)
        elif setting == "v_flip":
            return cv.flip(frame, 0)
        elif setting == "hv_flip":
            return cv.flip(frame, -1)

    def rotate_img(self, frame):
        setting = self.orient_prop[1]
        if setting == "0":
            return frame
        elif setting == "90":
            return cv.rotate(frame, cv.ROTATE_90_CLOCKWISE)
        elif setting == "180":
            return cv.rotate(frame, cv.ROTATE_180)
        elif setting == "270":
            return cv.rotate(frame, cv.ROTATE_90_COUNTERCLOCKWISE)

    def change_perspective(self, frame):
        if self.extrinsic_prop is not None:
            return cv.warpPerspective(frame, *self.extrinsic_prop)
        else:
            return frame

    def set_intrinsic_prop(self, cal_ok, map_x, map_y):
        if cal_ok:
            self.intrinsic_prop = (map_x, map_y)
        else:
            self.intrinsic_prop = None

    def set_extrinsic_prop(self, cal_ok, trans_mat, output_size):
        if cal_ok:
            self.extrinsic_prop = (trans_mat, output_size)
        else:
            self.extrinsic_prop = None

    def set_orient_prop(self, flip, rotate):
        self.orient_prop = (flip, rotate)


if __name__ == "__main__":
    s = StreamWorker()
