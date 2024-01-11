import logging
from queue import Empty

import cv2 as cv
import numpy as np

from defs import QtCore, Signal
from motion_analysis_2d.custom_components import StaticTracker
from motion_analysis_2d.funcs import angle_vec


class TrackingWorker(QtCore.QObject):
    finished = Signal()
    tracking_failed = Signal(str, int)
    reached_end = Signal()
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
        logging.debug(f"No of frames set to {no_of_frames} in tracking worker.")

    def clear_data(self):
        self.analysis_data = {"angle": {}, "distance": {}}
        self.tracking_data = {}
        self.trackers = {}
        logging.debug("Tracking data cleared.")

    def add_tracker(self, name, bbox_pos, bbox_size, offset, tracker_type="Static"):
        self.mutex.lock()
        if self.tracking_data.get(name) is None:
            self.tracking_data[name] = {
                "frame_no": np.arange(self.no_of_frames) + 1,
                "time": np.full(self.no_of_frames, np.nan, dtype=float),
                "bbox": np.full((self.no_of_frames, 4), np.nan, dtype=float),
                "target": np.full((self.no_of_frames, 2), np.nan, dtype=float),
            }
            logging.debug(f"New tracking data for {name} added.")

        bbox = (*bbox_pos, *bbox_size)
        target = bbox_to_target(*bbox, *offset)
        self.tracking_data[name]["time"][self.frame_no - 1] = self.timestamp
        self.tracking_data[name]["bbox"][self.frame_no - 1] = bbox
        self.tracking_data[name]["target"][self.frame_no - 1] = target

        try:
            if tracker := self.tracking_data.get(name) is not None:
                del tracker

            tracker = self.create_tracker(tracker_type)
            tracker.init(self.frame, bbox)
            self.trackers[name] = (tracker, offset, tracker_type)
            logging.debug(f"Tracker for {name} created.")

        except Exception as e:
            self.tracking_data.pop(name, None)
            self.trackers.pop(name, None)
            self.add_tracker_failed.emit(name, e)
            logging.warning(f"Create tracker failed for {name}.")
        self.mutex.unlock()

    def edit_tracker(self, name, new_name, new_tracker_type):
        self.mutex.lock()

        if new_name != name:
            self.tracking_data[new_name] = self.tracking_data[name]
            self.trackers[new_name] = self.trackers[name]
            del self.tracking_data[name]
            del self.trackers[name]

        bbox = self.tracking_data[new_name]["bbox"][self.frame_no - 1]
        _, offset, _ = self.trackers[new_name]

        if (~np.isnan(bbox)).any():
            tracker = self.create_tracker(new_tracker_type)
            tracker.init(self.frame, bbox.astype(np.int32))
            self.trackers[new_name] = (tracker, offset, new_tracker_type)

        if new_name != name:
            for angle in self.analysis_data["angle"].values():
                for i, parent_name in enumerate(angle["trackers"]):
                    if parent_name == name:
                        angle["trackers"][i] = new_name
            for distance in self.analysis_data["distance"].values():
                for i, parent_name in enumerate(distance["trackers"]):
                    if parent_name == name:
                        distance["trackers"][i] = new_name
        self.mutex.unlock()

    def add_angle(self, name, start1, end1, start2, end2):
        self.mutex.lock()
        angle_data = self.analysis_data["angle"]
        if angle_data.get(name) is None:
            angle_data[name] = {
                "frame_no": np.arange(self.no_of_frames) + 1,
                "angle": np.full(self.no_of_frames, np.nan, dtype=float),
                "trackers": [start1, end1, start2, end2],
            }
            logging.debug(f"New angle data for {name} added.")

        vec1_angle = angle_vec(
            self.tracking_data[end1]["target"] - self.tracking_data[start1]["target"]
        )
        vec2_angle = angle_vec(
            self.tracking_data[end2]["target"] - self.tracking_data[start2]["target"]
        )

        angle_data[name]["angle"] = vec2_angle - vec1_angle
        logging.debug(f"Angle data for {name} updated.")
        self.mutex.unlock()

    def edit_angle(self, name, new_name):
        self.mutex.lock()
        if new_name != name:
            self.analysis_data["angle"][new_name] = self.analysis_data["angle"][name]
            del self.analysis_data["angle"][name]
        self.mutex.unlock()

    def add_distance(self, name, start, end):
        self.mutex.lock()
        distance_data = self.analysis_data["distance"]
        if distance_data.get(name) is None:
            distance_data[name] = {
                "frame_no": np.arange(self.no_of_frames) + 1,
                "distance": np.full((self.no_of_frames, 2), np.nan, dtype=float),
                "trackers": [start, end],
            }
            logging.debug(f"New distance data for {name} added.")

        distance_data[name]["distance"] = (
            self.tracking_data[end]["target"] - self.tracking_data[start]["target"]
        )
        logging.debug(f"Distance data for {name} updated.")
        self.mutex.unlock()

    def edit_distance(self, name, new_name):
        self.mutex.lock()
        if new_name != name:
            self.analysis_data["distance"][new_name] = self.analysis_data["distance"][
                name
            ]
            del self.analysis_data["distance"][name]
        self.mutex.unlock()

    def reset_trackers(self):
        self.mutex.lock()
        for name, (_, offset, tracker_type) in self.trackers.items():
            bbox = self.tracking_data[name]["bbox"][self.frame_no - 1]
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
        logging.debug(f"Tracker {name} remove from tracking worker.")

    def remove_angle(self, name):
        self.mutex.lock()
        self.analysis_data["angle"].pop(name, None)
        self.mutex.unlock()
        logging.debug(f"Angle {name} remove from tracking worker.")

    def remove_distance(self, name):
        self.mutex.lock()
        self.analysis_data["distance"].pop(name, None)
        self.mutex.unlock()
        logging.debug(f"Distance {name} remove from tracking worker.")

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
                if frame_no >= self.no_of_frames != 0:
                    self.reached_end.emit()

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
                self.tracking_data[name]["time"][frame_no - 1] = timestamp
                self.tracking_data[name]["bbox"][frame_no - 1] = bbox
                self.tracking_data[name]["target"][frame_no - 1] = target
                self.mutex.unlock()
            else:
                self.tracking_failed.emit(name, frame_no)
                break
        else:
            self.update_angle(frame_no)
            self.update_distance(frame_no)

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
                    self.tracking_data[end1]["target"][frame_no - 1]
                    - self.tracking_data[start1]["target"][frame_no - 1]
                ]
            )[0]
            vec2_angle = angle_vec(
                [
                    self.tracking_data[end2]["target"][frame_no - 1]
                    - self.tracking_data[start2]["target"][frame_no - 1]
                ]
            )[0]
            angle_data[name]["angle"][frame_no - 1] = vec2_angle - vec1_angle

    def update_distance(self, frame_no):
        distance_data = self.analysis_data["distance"]
        for name, data in distance_data.items():
            start, end = data["trackers"]

            distance_data[name]["distance"][frame_no - 1] = (
                self.tracking_data[end]["target"][frame_no - 1]
                - self.tracking_data[start]["target"][frame_no - 1]
            )

    def set_stop(self):
        self.stop_flag = True

    def set_tracking_data(self, data):
        self.tracking_data.update(data)


def bbox_to_target(x, y, wx, wy, offset_x, offset_y):
    centre_x, centre_y = (x + wx / 2, y + wy / 2)
    return centre_x + offset_x, centre_y + offset_y


if __name__ == "__main__":
    s = TrackingWorker()
