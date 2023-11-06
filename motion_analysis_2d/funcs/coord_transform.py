import cv2

from defs import QtGui


def data_to_bbox(x, y, wx, wy):
    return x - wx / 2, y - wy / 2, wx, wy


def bbox_to_data(bbox):
    wx, wy = bbox[2:]
    x = bbox[0] + wx / 2
    y = bbox[1] + wy / 2
    return x, y, wx, wy


def roi_to_data(roi):
    x, y = roi.pos() + roi.size() / 2
    wx, wy = roi.size()
    return x, y, wx, wy


def data_to_roi(x, y, wx, wy):
    pos = (x - wx / 2, y - wy / 2)
    size = (wx, wy)
    return pos, size


def data_to_roi(x, y, wx, wy):
    pos = (x - wx / 2, y - wy / 2)
    size = (wx, wy)
    return pos, size


def bbox_to_target(x, y, wx, wy, offset_x, offset_y):
    centre_x, centre_y = (x + wx / 2, y + wy / 2)
    return centre_x + offset_x, centre_y + offset_y


def opencv_draw_rect(frame, x, y, wx, wy):
    cv2.rectangle(
        frame,
        (int(x - wx / 2), int(y - wy / 2)),
        (int(x + wx / 2), int(y + wy / 2)),
        (255, 0, 0),
        2,
        1,
    )


def cvImg_to_qImg(cvImg):
    height, width, channel = cvImg.shape
    bytesPerLine = 3 * width
    cvImg = cv2.cvtColor(cvImg, cv2.COLOR_BGR2RGB)
    return QtGui.QImage(
        cvImg.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888
    )
