import json

import numpy as np


def save_json(path, tracker_properties, tracking_data, current_frame):
    save_data = {"tracker_properties": {}, "tracking_data": {}}
    save_data["tracker_properties"].update(tracker_properties)

    for tracker_name, tracker_data in tracking_data.items():
        save_params = {}
        for param_label, param_data in tracker_data.items():
            save_params[param_label] = param_data.tolist()

        save_data["tracking_data"][tracker_name] = save_params

    save_data["current_frame"] = current_frame

    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, sort_keys=False, indent=4)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        save_data = json.load(f)

    tracker_properties = save_data["tracker_properties"]

    tracking_data = {}
    for tracker_name, tracker_data in save_data["tracking_data"].items():
        save_params = {}
        for param_label, param_data in tracker_data.items():
            save_params[param_label] = np.array(param_data)

        tracking_data[tracker_name] = save_params

    current_frame = save_data["current_frame"]

    return tracker_properties, tracking_data, current_frame
