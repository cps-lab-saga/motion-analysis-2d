from queue import Empty

import cv2 as cv
import numpy as np

from defs import QtCore, Signal
from motion_analysis_2d.custom_components import StaticTracker
from motion_analysis_2d.funcs import bbox_to_target, angle_vec


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
        self.analysis_data = {"angle": {}, "distance": {}}

        self.stream_queue = stream_queue

        self.frame = None
        self.frame_no = 0
        self.timestamp = 0
        self.no_of_frames = 0

        self.stop_flag = False
        self.mutex = QtCore.QMutex()

    def set_props(self, no_of_frames):
        self.no_of_frames = no_of_frames

    def clear_data(self):
        self.analysis_data = {"angle": {}, "distance": {}}
        self.tracking_data = {}
        self.trackers = {}

    def add_tracker(self, name, bbox_pos, bbox_size, offset, tracker_type="Static"):
        self.mutex.lock()
        if self.tracking_data.get(name) is None:
            self.tracking_data[name] = {
                "frame_no": np.arange(self.no_of_frames + 1),
                "time": np.full(self.no_of_frames + 1, np.nan, dtype=float),
                "bbox": np.full((self.no_of_frames + 1, 4), np.nan, dtype=float),
                "target": np.full((self.no_of_frames + 1, 2), np.nan, dtype=float),
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

    def add_angle(self, name, start1, end1, start2, end2):
        self.mutex.lock()
        angle_data = self.analysis_data["angle"]
        if angle_data.get(name) is None:
            angle_data[name] = {
                "frame_no": np.arange(self.no_of_frames + 1),
                "angle": np.full(self.no_of_frames + 1, np.nan, dtype=float),
                "trackers": (start1, end1, start2, end2),
            }

        vec1_angle = angle_vec(
            self.tracking_data[end1]["target"] - self.tracking_data[start1]["target"]
        )
        vec2_angle = angle_vec(
            self.tracking_data[end2]["target"] - self.tracking_data[start2]["target"]
        )

        angle_data[name]["angle"] = vec2_angle - vec1_angle
        self.mutex.unlock()

    def reset_trackers(self):
        self.mutex.lock()
        for name, (_, offset, tracker_type) in self.trackers.items():
            bbox = self.tracking_data[name]["bbox"][self.frame_no]
            if (~np.isnan(bbox)).any():
                tracker = self.create_tracker(tracker_type)
                tracker.init(self.frame, bbox.astype(np.int32))
                self.trackers[name] = (tracker, offset, tracker_type)
        self.mutex.unlock()

    def remove_tracker(self, name):
        self.mutex.lock()
        self.tracking_data.pop(name, None)
        self.trackers.pop(name, None)
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
                (frame_no, timestamp, frame, track) = self.stream_queue.get(
                    block=True, timeout=1
                )
                if track:
                    self.run_trackers(frame_no, timestamp, frame)
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
                break
        else:
            self.update_angle(frame_no)

        self.mutex.lock()
        self.frame_no = frame_no
        self.frame = frame
        self.timestamp = timestamp
        self.mutex.unlock()

    def update_angle(self, frame_no):
        angle_data = self.analysis_data["angle"]
        for name, data in angle_data.items():
            start1, end1, start2, end2 = data["trackers"]

            vec1_angle = angle_vec(
                [
                    self.tracking_data[end1]["target"][frame_no]
                    - self.tracking_data[start1]["target"][frame_no]
                ]
            )[0]
            vec2_angle = angle_vec(
                [
                    self.tracking_data[end2]["target"][frame_no]
                    - self.tracking_data[start2]["target"][frame_no]
                ]
            )[0]
            angle_data[name]["angle"][frame_no] = vec2_angle - vec1_angle

    def set_stop(self):
        self.stop_flag = True

    def set_tracking_data(self, data):
        self.tracking_data.update(data)


if __name__ == "__main__":
    s = TrackingWorker()
