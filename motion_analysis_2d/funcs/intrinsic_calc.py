import csv
import json
import logging
from pathlib import Path

import cv2 as cv
import numpy as np

criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)


def find_points(img, nx, ny, pattern="Checkerboard", spacing=1):
    objpoints = np.zeros((nx * ny, 3), np.float32)
    objpoints[:, :2] = np.mgrid[0:nx, 0:ny].T.reshape(-1, 2) * spacing

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    if pattern == "Checkerboard":
        ret, corners = cv.findChessboardCorners(gray, (nx, ny), None)

        if not ret:
            return img, ret, None, None

        imgpoints = cv.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)
        return img, ret, objpoints, imgpoints

    elif pattern == "Circles":
        ret, imgpoints = cv.findCirclesGrid(
            gray, (nx, ny), flags=cv.CALIB_CB_SYMMETRIC_GRID + cv.CALIB_CB_CLUSTERING
        )

        return (img, ret, objpoints, imgpoints) if ret else (img, ret, None, None)

    elif pattern == "Asymmetric Circles":
        ret, imgpoints = cv.findCirclesGrid(
            gray, (nx, ny), flags=cv.CALIB_CB_ASYMMETRIC_GRID + cv.CALIB_CB_CLUSTERING
        )

        return (img, ret, objpoints, imgpoints) if ret else (img, ret, None, None)


def calibrate_camera(img_files, nx=9, ny=6):
    objpoints = []
    imgpoints = []
    for fname in img_files:
        img = cv.imread(str(fname))
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        objp = np.zeros((nx * ny, 3), np.float32)
        objp[:, :2] = np.mgrid[0:nx, 0:ny].T.reshape(-1, 2)

        ret, corners = cv.findChessboardCorners(gray, (nx, ny), None)
        logging.info(f"{fname} - {ret}")
        if ret:
            objpoints.append(objp)

            corners2 = cv.cornerSubPix(gray, corners, (5, 5), (-1, -1), criteria)
            imgpoints.append(corners2)

    return cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)


def undistort(img, intrinsic_matrix, distortion_coeffs):
    h, w = img.shape[:2]
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(
        intrinsic_matrix, distortion_coeffs, (w, h), 1, (w, h)
    )

    dst = cv.undistort(img, intrinsic_matrix, distortion_coeffs, None, newcameramtx)

    # # crop the image
    # x, y, w, h = roi
    # dst = dst[y:y + h, x:x + w]

    return dst


def get_undistort_funcs(shape, intrinsic_matrix, distortion_coeffs, fisheye=False):
    h, w = shape[:2]

    if fisheye:
        newcameramtx = cv.fisheye.estimateNewCameraMatrixForUndistortRectify(
            intrinsic_matrix, distortion_coeffs, (w, h), np.eye(3), balance=0
        )
        map_x, map_y = cv.fisheye.initUndistortRectifyMap(
            intrinsic_matrix,
            distortion_coeffs,
            np.eye(3),
            newcameramtx,
            (w, h),
            cv.CV_16SC2,
        )
    else:
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(
            intrinsic_matrix,
            distortion_coeffs,
            (w, h),
            1,
            (w, h),
        )
        map_x, map_y = cv.initUndistortRectifyMap(
            intrinsic_matrix,
            distortion_coeffs,
            None,
            newcameramtx,
            (w, h),
            cv.CV_16SC2,
        )

    return map_x, map_y, newcameramtx


if __name__ == "__main__":
    img_dir = Path("img_cal").resolve()

    nx = 9
    ny = 6
    (
        rms_error,
        intrinsic_matrix,
        distortion_coeffs,
        rotation_vecs,
        translation_vecs,
    ) = calibrate_camera(img_dir.glob("*.JPG"), nx, ny)
    fx = intrinsic_matrix[0, 0]
    fy = intrinsic_matrix[1, 1]
    cx = intrinsic_matrix[0, 2]
    cy = intrinsic_matrix[1, 2]
    s = intrinsic_matrix[0, 1]

    k1, k2, p1, p2, k3 = distortion_coeffs[0]

    np.savez(img_dir / "intrinsic_cal1.npz", K=intrinsic_matrix, D=distortion_coeffs)
    np.savez(
        img_dir / "intrinsic_cal2.npz",
        fx=fx,
        fy=fy,
        cx=cx,
        cy=cy,
        s=s,
        k1=k1,
        k2=k2,
        p1=p1,
        p2=p2,
        k3=k3,
    )
    np.savez(
        img_dir / "intrinsic_cal3.npz",
        K=intrinsic_matrix,
        k1=k1,
        k2=k2,
        p1=p1,
        p2=p2,
        k3=k3,
    )

    with open(img_dir / "intrinsic_cal1.json", "w") as f:
        json.dump(
            dict(K=intrinsic_matrix.tolist(), D=distortion_coeffs.tolist()),
            f,
            sort_keys=False,
            indent=4,
        )
    with open(img_dir / "intrinsic_cal2.json", "w") as f:
        json.dump(
            dict(fx=fx, fy=fy, cx=cx, cy=cy, s=s, k1=k1, k2=k2, p1=p1, p2=p2, k3=k3),
            f,
            sort_keys=False,
            indent=4,
        )
    with open(img_dir / "intrinsic_cal3.json", "w") as f:
        json.dump(
            dict(K=intrinsic_matrix.tolist(), k1=k1, k2=k2, p1=p1, p2=p2, k3=k3),
            f,
            sort_keys=False,
            indent=4,
        )

    with open(img_dir / "intrinsic_cal1.csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        for param in ["fx", "fy", "cx", "cy", "s", "k1", "k2", "p1", "p2", "k3"]:
            writer.writerow([param, eval(param)])

    with open(img_dir / "intrinsic_cal1.txt", "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        for param in ["fx", "fy", "cx", "cy", "s", "k1", "k2", "p1", "p2", "k3"]:
            writer.writerow([f"{param}={eval(param)}"])
