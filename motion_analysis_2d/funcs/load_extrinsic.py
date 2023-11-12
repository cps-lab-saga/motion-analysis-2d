import json

import cv2 as cv
import numpy as np


def load_extrinsic(file_path):
    with open(file_path, mode="r") as f:
        cal_data = json.load(f)
        corners_in = np.array(cal_data["corners_in"])
        corners_out = np.array(cal_data["corners_out"])
        size = np.array(cal_data["output_size"]).astype(np.int_)
        scaling = np.array(cal_data["scaling"])

        M, mask = cv.findHomography(corners_in, corners_out, cv.RANSAC)

    return M, mask, size, scaling


def save_warp_points(img_points, obj_points, file_path):
    save_data = {
        "corners_in": img_points,
        "corners_out": obj_points,
        "output_size": (
            np.array(obj_points).max(axis=0) - np.array(obj_points).min(axis=0)
        ).tolist(),
        "scaling": 1,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, sort_keys=False, indent=4)
