import json

import cv2 as cv
import numpy as np


def load_extrinsic(file_path):
    with open(file_path, mode="r") as f:
        cal_data = json.load(f)
        corners_in = np.array(cal_data["corners_in"])
        corners_out = np.array(cal_data["corners_out"])
        size = np.array(cal_data["output_size"])

        M, mask = cv.findHomography(corners_in, corners_out, cv.RANSAC)

    return M, mask, size
