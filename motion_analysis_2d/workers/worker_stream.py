from time import sleep

import cv2 as cv

from defs import QtCore, Signal


class StreamWorker(QtCore.QObject):
    stream_props = Signal(float, int)
    finished = Signal()
    progress = Signal()

    def __init__(
        self,
        path,
        stream_queue,
        intrinsic_cal,
        extrinsic_cal,
        orient,
        *args,
        **kwargs,
    ):
        super().__init__()

        self.path = path
        self.stop_flag = False
        self.stream_queue = stream_queue
        self.cap = None
        self.intrinsic_cal = intrinsic_cal
        self.extrinsic_cal = extrinsic_cal
        self.orient = orient

        self.frame_no = 0
        self.timestamp = 0
        self.frame_rate = 0
        self.no_of_frames = 0
        self.frame = None

        self.stop_flag = False
        self.play_flag = False
        self.track_flag = False
        self.mutex = QtCore.QMutex()

    def stream(self):
        self.stop_flag = False
        self.cap = cv.VideoCapture(str(self.path))

        self.frame_rate = self.cap.get(cv.CAP_PROP_FPS)
        self.no_of_frames = int(self.cap.get(cv.CAP_PROP_FRAME_COUNT))
        self.stream_props.emit(self.frame_rate, self.no_of_frames)

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

    def read_single_frame(self):
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
                self.track_flag,
            )
        )
        self.mutex.unlock()

    def process_frame(self, frame):
        frame = self.intrinsic_cal.undistort_map(frame)
        frame = self.extrinsic_cal.change_perspective(frame)
        frame = self.orient.orient_img(frame)
        return frame

    def move_frame_forwards(self):
        self.read_single_frame()

    def move_frame_backwards(self):
        self.cap.set(cv.CAP_PROP_POS_FRAMES, self.frame_no - 2)
        self.read_single_frame()

    def read_current_frame(self):
        self.read_single_frame()
        self.cap.set(cv.CAP_PROP_POS_FRAMES, self.frame_no - 1)

    def move_frame_to(self, frame_no):
        self.cap.set(cv.CAP_PROP_POS_FRAMES, frame_no)
        self.read_single_frame()

    def set_stop(self):
        self.stop_flag = True

    def set_play(self):
        self.play_flag = True

    def set_pause(self):
        self.play_flag = False

    def set_tracking(self, track):
        self.track_flag = track


if __name__ == "__main__":
    s = StreamWorker()
