import csv
import json

import numpy as np


def save_tracking_data(
    path, tracker_properties, analysis_properties, tracking_data, current_frame
):
    save_data = {
        "tracker_properties": {},
        "analysis_properties": {},
        "tracking_data": {},
    }
    save_data["tracker_properties"].update(tracker_properties)
    save_data["analysis_properties"].update(analysis_properties)

    for tracker_name, tracker_data in tracking_data.items():
        save_params = {}
        for param_label, param_data in tracker_data.items():
            save_params[param_label] = param_data.tolist()

        save_data["tracking_data"][tracker_name] = save_params

    save_data["current_frame"] = current_frame

    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, sort_keys=False, indent=4)


def load_tracking_data(path):
    with open(path, "r", encoding="utf-8") as f:
        save_data = json.load(f)

    tracker_properties = save_data["tracker_properties"]
    analysis_properties = save_data.get("analysis_properties")
    if analysis_properties is None:
        analysis_properties = {
            "angle": {
                "name": [],
                "start1": [],
                "end1": [],
                "start2": [],
                "end2": [],
                "color": [],
            },
            "distance": {"name": [], "start": [], "end": [], "color": []},
        }

    tracking_data = {}
    for tracker_name, tracker_data in save_data["tracking_data"].items():
        save_params = {}
        for param_label, param_data in tracker_data.items():
            save_params[param_label] = np.array(param_data)

        tracking_data[tracker_name] = save_params

    current_frame = save_data["current_frame"]

    return tracker_properties, analysis_properties, tracking_data, current_frame


def export_csv(path, tracking_data):
    header = ["frame_no", "time"]
    targets = []
    params = next(iter(tracking_data.values()))
    index = [np.expand_dims(params[x], axis=1) for x in header]
    for name, params in tracking_data.items():
        header.extend([f"{name}-x", f"{name}-y"])
        targets.append(params["target"])

    data = np.concatenate(index + targets, axis=1)

    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(header)
        np.savetxt(f, data, delimiter=",", fmt="%.4f")


if __name__ == "__main__":
    data = {}
    no_of_frames = 50
    for name in ["test1", "test2", "test3", "test4"]:
        data[name] = {
            "frame_no": np.arange(no_of_frames),
            "time": np.full(no_of_frames, 1, dtype=float),
            "bbox": np.full((no_of_frames, 4), 2, dtype=float),
            "target": np.full((no_of_frames, 2), 3, dtype=float),
        }
    export_csv("test.csv", data)
