import json

import cv2 as cv
import numpy as np


def load_extrinsic(file_path):
    with open(file_path, mode="r") as f:
        cal_data = json.load(f)
        if cal_data["corners_in"] is not None:
            corners_in = np.array(cal_data["corners_in"]).astype(np.int_)
            corners_out = np.array(cal_data["corners_out"]).astype(np.int_)
            size = np.array(cal_data["output_size"]).astype(np.int_)
            scaling = cal_data["scaling"]

            M, mask = cv.findHomography(corners_in, corners_out, cv.RANSAC)

        else:
            scaling = cal_data["scaling"]
            M, mask, size = None, None, None

    return M, mask, size, scaling


def save_perspective_points(img_points, obj_points, output_size_real, file_path):
    corners_in = np.array(img_points)
    corners_out = np.array(obj_points)

    if len(img_points) == 2:
        pixel_distance = np.linalg.norm(corners_in[1] - corners_in[0])
        real_distance = np.linalg.norm(corners_out[1] - corners_out[0])
        scaling = np.round(pixel_distance / real_distance, 2)
        save_data = {
            "corners_in": None,
            "corners_out": None,
            "output_size": None,
            "scaling": scaling,
        }

    else:
        in_width, in_height = corners_in.max(axis=0) - corners_in.min(axis=0)
        out_width, out_height = corners_out.max(axis=0) - corners_out.min(axis=0)
        scaling = np.mean([in_width / out_width, in_height / out_height])

        output_size = np.array(output_size_real) * scaling
        corners_out *= scaling
        save_data = {
            "corners_in": corners_in.tolist(),
            "corners_out": corners_out.tolist(),
            "output_size": output_size.tolist(),
            "scaling": scaling,
        }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, sort_keys=False, indent=4)
