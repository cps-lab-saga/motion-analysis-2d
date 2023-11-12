import json

import cv2 as cv
import numpy as np


def load_extrinsic(file_path):
    with open(file_path, mode="r") as f:
        cal_data = json.load(f)
        corners_in = np.array(cal_data["corners_in"]).astype(np.int_)
        corners_out = np.array(cal_data["corners_out"]).astype(np.int_)
        size = np.array(cal_data["output_size"]).astype(np.int_)
        scaling = cal_data["scaling"]

        M, mask = cv.findHomography(corners_in, corners_out, cv.RANSAC)

    return M, mask, size, scaling


def save_warp_points(img_points, obj_points, file_path):
    corners_in = np.array(img_points)
    corners_out = np.array(obj_points)
    in_width, in_height = np.array(img_points).max(axis=0) - np.array(img_points).min(
        axis=0
    )
    out_width, out_height = np.array(obj_points).max(axis=0) - np.array(obj_points).min(
        axis=0
    )
    scaling = np.round(np.mean([in_width / out_width, in_height / out_height]), 2)
    corners_out *= scaling
    save_data = {
        "corners_in": corners_in.tolist(),
        "corners_out": corners_out.tolist(),
        "output_size": (
            np.array(corners_out).max(axis=0) - np.array(corners_out).min(axis=0)
        ).tolist(),
        "scaling": scaling,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, sort_keys=False, indent=4)
