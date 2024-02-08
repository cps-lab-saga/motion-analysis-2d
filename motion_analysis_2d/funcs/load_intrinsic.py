import json
import re
from pathlib import Path
from xml.dom import minidom

import numpy as np


def load_intrinsic(file_path):
    if file_path.suffix == ".npz":
        return load_intrinsic_npz(file_path)
    elif file_path.suffix == ".json":
        return load_intrinsic_json(file_path)
    elif file_path.suffix in [".csv", ".txt"]:
        return load_intrinsic_txt(file_path)
    elif file_path.suffix == ".xml":
        return load_intrinsic_xml(file_path)


def load_intrinsic_npz(file_path):
    with np.load(file_path, mmap_mode="r") as cal_data:
        if "fisheye" in cal_data.files:
            fisheye = cal_data["fisheye"]
        else:
            fisheye = False

        if "K" in cal_data.files:
            K = cal_data["K"]
        else:
            fx = cal_data["fx"]
            fy = cal_data["fy"]
            cx = cal_data["cx"]
            cy = cal_data["cy"]
            s = cal_data["s"] if "s" in cal_data.files else 0

            K = np.asarray([[fx, s, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

        if "D" in cal_data.files:
            D = np.asarray(cal_data["D"], dtype=float)
        else:
            if fisheye:
                k1 = cal_data["k1"]
                k2 = cal_data["k2"]
                k3 = cal_data["k3"]
                k4 = cal_data["k4"]
                D = np.asarray([[k1, k2, k3, k4]], dtype=float)
            else:
                k1 = cal_data["k1"]
                k2 = cal_data["k2"]
                p1 = cal_data["p1"]
                p2 = cal_data["p2"]
                k3 = cal_data["k3"]
                D = np.asarray([[k1, k2, p1, p2, k3]], dtype=float)
    return K, D, fisheye


def load_intrinsic_json(file_path):
    with open(file_path, mode="r") as f:
        cal_data = json.load(f)

    if "fisheye" in cal_data:
        fisheye = cal_data["fisheye"]
    else:
        fisheye = False

    if "K" in cal_data.keys():
        K = np.array(cal_data["K"])
    else:
        fx = cal_data["fx"]
        fy = cal_data["fy"]
        cx = cal_data["cx"]
        cy = cal_data["cy"]
        s = cal_data["s"] if "s" in cal_data.keys() else 0

        K = np.asarray([[fx, s, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

    if "D" in cal_data.keys():
        D = np.asarray(cal_data["D"], dtype=float)
    else:
        if fisheye:
            k1 = cal_data["k1"]
            k2 = cal_data["k2"]
            k3 = cal_data["k3"]
            k4 = cal_data["k4"]
            D = np.asarray([[k1, k2, k3, k4]], dtype=float)
        else:
            k1 = cal_data["k1"]
            k2 = cal_data["k2"]
            p1 = cal_data["p1"]
            p2 = cal_data["p2"]
            k3 = cal_data["k3"]
            D = np.asarray([[k1, k2, p1, p2, k3]], dtype=float)

    return K, D, fisheye


def load_intrinsic_txt(file_path):
    with open(file_path, mode="r") as f:
        cal_data = {}
        for line in f:
            k, v = re.split("[,=\t]", line)
            cal_data[k.strip()] = float(v)

    if "fisheye" in cal_data:
        fisheye = cal_data["fisheye"]
    else:
        fisheye = False

    fx = cal_data["fx"]
    fy = cal_data["fy"]
    cx = cal_data["cx"]
    cy = cal_data["cy"]
    s = cal_data["s"] if "s" in cal_data.keys() else 0

    K = np.asarray([[fx, s, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

    if fisheye:
        k1 = cal_data["k1"]
        k2 = cal_data["k2"]
        k3 = cal_data["k3"]
        k4 = cal_data["k4"]
        D = np.asarray([[k1, k2, k3, k4]], dtype=float)
    else:
        k1 = cal_data["k1"]
        k2 = cal_data["k2"]
        p1 = cal_data["p1"]
        p2 = cal_data["p2"]
        k3 = cal_data["k3"]
        D = np.asarray([[k1, k2, p1, p2, k3]], dtype=float)

    return K, D, fisheye


def load_intrinsic_xml(file_path):
    with open(file_path, mode="r") as f:
        dom = minidom.parse(f)
        cal_data = dom.getElementsByTagName("calibration")[0]
        fisheye = cal_data.getElementsByTagName("fisheye")[0].childNodes[0].data
        if fisheye is None:
            fisheye = False

        fx = cal_data.getElementsByTagName("fx")[0].childNodes[0].data
        fy = cal_data.getElementsByTagName("fy")[0].childNodes[0].data
        cx = cal_data.getElementsByTagName("cx")[0].childNodes[0].data
        cy = cal_data.getElementsByTagName("cy")[0].childNodes[0].data
        s = cal_data.getElementsByTagName("skew")[0].childNodes[0].data
        K = np.asarray([[fx, s, cx], [0, fy, cy], [0, 0, 1]], dtype=float)

        if fisheye:
            k1 = cal_data.getElementsByTagName("k1")[0].childNodes[0].data
            k2 = cal_data.getElementsByTagName("k2")[0].childNodes[0].data
            k3 = cal_data.getElementsByTagName("k3")[0].childNodes[0].data
            k4 = cal_data.getElementsByTagName("k4")[0].childNodes[0].data
            D = np.asarray([[k1, k2, k3, k4]], dtype=float)
        else:
            k1 = cal_data.getElementsByTagName("k1")[0].childNodes[0].data
            k2 = cal_data.getElementsByTagName("k2")[0].childNodes[0].data
            p1 = cal_data.getElementsByTagName("p1")[0].childNodes[0].data
            p2 = cal_data.getElementsByTagName("p2")[0].childNodes[0].data
            k3 = cal_data.getElementsByTagName("k3")[0].childNodes[0].data
            D = np.asarray([[k1, k2, p1, p2, k3]], dtype=float)

        return K, D, fisheye


if __name__ == "__main__":
    img_dir = Path("cal_img").resolve()

    for file_name in img_dir.glob("intrinsic_cal*"):
        f = Path(file_name).resolve()

        intrinsic_matrix, distortion_coeffs = load_intrinsic(f)

        print(f"{f.name}: K = {intrinsic_matrix}, D = {distortion_coeffs}")
