import numpy as np
from scipy import signal


def angle_vec(vec1: np.array) -> np.array:
    """
    Calculate anticlockwise angle of vector from x-axis

    :param vec1: vectors to calculate angle from
    :type vec1: 2d numpy array of vectors
    :return: angles
    :rtype: 2d numpy array of angles
    """
    mag1 = np.linalg.norm(vec1, axis=1)
    vec1_hat = vec1 / mag1.reshape(-1, 1)
    vec2_hat = np.array([1, 0])

    cross_product = np.cross(vec1_hat, vec2_hat)
    dot_product = np.dot(vec1_hat, vec2_hat)
    # dot_product = np.dot(vec1_hat, vec2_hat.T)
    # dot_product = np.einsum("ij, j->i", vec1_hat, vec2_hat)
    angle = np.degrees(np.arccos(dot_product))
    angle[cross_product < 0] = -angle[cross_product < 0]
    return angle


def angle_between(vec1: np.array, vec2: np.array) -> np.array:
    """
    Calculate anticlockwise angle between two vectors

    :param vec1: vectors to calculate angle from
    :type vec1: 2d numpy array of vectors
    :param vec2: vectors to calculate angle from
    :type vec2: 2d numpy array of vectors
    :return: angles
    :rtype: 2d numpy array of angles
    """
    mag1 = np.linalg.norm(vec1, axis=1)
    mag2 = np.linalg.norm(vec2, axis=1)

    vec1_hat = vec1 / mag1.reshape(-1, 1)
    vec2_hat = vec2 / mag2.reshape(-1, 1)

    cross_product = np.cross(vec1_hat, vec2_hat)
    # dot_product = np.dot(vec1_hat, vec2_hat.T)
    dot_product = np.einsum("ij, ij->i", vec1_hat, vec2_hat)
    angle = np.degrees(np.arccos(dot_product))
    angle[cross_product < 0] = -angle[cross_product < 0]
    return angle


def filter_lowpass(data, fs, highcut):
    b, a = butter_lowpass(highcut, fs)
    return signal.filtfilt(b, a, data)


def butter_lowpass(highcut, fs, order=3):
    nyq = 0.5 * fs
    high = highcut / nyq
    b, a = signal.butter(order, high, btype="lowpass")
    return b, a
