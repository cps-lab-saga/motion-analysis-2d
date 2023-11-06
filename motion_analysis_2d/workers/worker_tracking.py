from queue import Empty

import cv2 as cv
import numpy as np

from defs import QtCore, Signal
from motion_analysis_2d.custom_components import StaticTracker
from motion_analysis_2d.funcs import bbox_to_target


class TrackingWorker(QtCore.QObject):
    finished = Signal()
    progress = Signal()
    tracking_failed = Signal(str, int)
    add_tracker_failed = Signal(str, object)

    def __init__(
        self,
        stream_queue,
    ):
        super().__init__()

        self.trackers = {}
        self.tracking_data = {}

        self.stream_queue = stream_queue

        self.frame = None
        self.frame_no = 0
        self.timestamp = 0
        self.no_of_frames = 0

        self.stop_flag = False
        self.track_flag = False
        self.mutex = QtCore.QMutex()

    def set_props(self, no_of_frames):
        self.no_of_frames = no_of_frames

    def clear_trackers(self):
        self.tracking_data = {}
        self.trackers = {}

    def reset_trackers(self):
        self.mutex.lock()
        for name, (_, offset, tracker_type) in self.trackers.items():
            bbox = self.tracking_data[name]["bbox"][self.frame_no]
            tracker = self.create_tracker(tracker_type)
            tracker.init(self.frame, bbox.astype(np.int32))
            self.trackers[name] = (tracker, offset, tracker_type)
        self.mutex.unlock()

    def remove_tracker(self, name):
        self.mutex.lock()
        self.tracking_data.pop(name, None)
        self.trackers.pop(name, None)
        self.mutex.unlock()

    def add_tracker(self, name, bbox_pos, bbox_size, offset, tracker_type):
        self.mutex.lock()
        if self.tracking_data.get(name) is None:
            self.tracking_data[name] = {
                "frame_no": np.arange(self.no_of_frames),
                "time": np.full(self.no_of_frames, np.nan, dtype=float),
                "bbox": np.full((self.no_of_frames, 4), np.nan, dtype=float),
                "target": np.full((self.no_of_frames, 2), np.nan, dtype=float),
            }

        bbox = (*bbox_pos, *bbox_size)
        target = bbox_to_target(*bbox, *offset)

        self.tracking_data[name]["time"][self.frame_no] = self.timestamp
        self.tracking_data[name]["bbox"][self.frame_no] = bbox
        self.tracking_data[name]["target"][self.frame_no] = target

        try:
            if tracker := self.tracking_data.get(name) is not None:
                del tracker

            tracker = self.create_tracker(tracker_type)
            tracker.init(self.frame, bbox)
            self.trackers[name] = (tracker, offset, tracker_type)
        except Exception as e:
            self.tracking_data.pop(name, None)
            self.trackers.pop(name, None)
            self.add_tracker_failed.emit(name, e)

        self.mutex.unlock()

    def create_tracker(self, tracker_type):
        if tracker_type == "CSRT":
            tracker = cv.TrackerCSRT_create()
        elif tracker_type == "KCF":
            tracker = cv.TrackerKCF_create()
        elif tracker_type == "MedianFlow":
            tracker = cv.legacy.TrackerMedianFlow_create()
        elif tracker_type == "Boosting":
            tracker = cv.legacy.TrackerBoosting_create()
        elif tracker_type == "MOSSE":
            tracker = cv.legacy.TrackerMOSSE_create()
        elif tracker_type == "MIL":
            tracker = cv.legacy.TrackerMIL_create()
        elif tracker_type == "Static":
            tracker = StaticTracker()
        else:
            raise NotImplementedError
        return tracker

    def run(self):
        self.stop_flag = False
        while not self.stop_flag:
            try:
                (frame_no, timestamp, frame) = self.stream_queue.get(
                    block=True, timeout=1
                )
                if self.track_flag:
                    success = self.run_trackers(frame_no, timestamp, frame)
                    if not success:
                        while not self.stream_queue.empty():
                            self.stream_queue.get()
                else:
                    self.frame_no, self.timestamp, self.frame = (
                        frame_no,
                        timestamp,
                        frame,
                    )

            except Empty:
                pass

        self.finished.emit()
        self.stop_flag = False
        self.deleteLater()

    def run_trackers(self, frame_no, timestamp, frame):
        for name, (tracker, offset, tracker_type) in self.trackers.items():
            ret, bbox = tracker.update(frame)
            if ret:
                bbox = bbox
                target = bbox_to_target(*bbox, *offset)

                self.mutex.lock()
                self.tracking_data[name]["time"][frame_no] = timestamp
                self.tracking_data[name]["bbox"][frame_no] = bbox
                self.tracking_data[name]["target"][frame_no] = target
                self.mutex.unlock()
            else:
                self.tracking_failed.emit(name, frame_no)
                return False
        self.mutex.lock()
        self.frame_no = frame_no
        self.frame = frame
        self.timestamp = timestamp
        self.mutex.unlock()
        return True

    def set_stop(self):
        self.stop_flag = True

    def set_tracking(self, track):
        self.track_flag = track


if __name__ == "__main__":
    s = TrackingWorker()
