import numpy as np
from scipy import signal


def angle_between(vec1, vec2):
    mag1 = np.linalg.norm(vec1, axis=1)
    mag2 = np.linalg.norm(vec2, axis=1)

    vec1_hat = vec1 / mag1.reshape(-1, 1)
    vec2_hat = vec2 / mag2.reshape(-1, 1)

    # dot_product = np.diag(vec1_hat @ vec2_hat.T)
    dot_product = np.einsum("ij, ij->i", vec1_hat, vec2_hat)
    angle = np.arccos(dot_product)
    return np.degrees(angle)


def angle_360(vec1, vec2):
    mag1 = np.linalg.norm(vec1, axis=1)
    mag2 = np.linalg.norm(vec2, axis=1)

    vec1_hat = vec1 / mag1.reshape(-1, 1)
    vec2_hat = vec2 / mag2.reshape(-1, 1)

    det = np.cross(vec1_hat, vec2_hat)
    dot_product = np.einsum("ij, ij->i", vec1_hat, vec2_hat)
    angle = np.arctan2(det, dot_product)
    return np.degrees(angle)


def distance(vec, ref_vec, ref_distance):
    return np.abs(vec / np.linalg.norm(ref_vec, axis=1).reshape(-1, 1) * ref_distance)


def filter_lowpass(data, fs, highcut):
    b, a = butter_lowpass(highcut, fs)
    return signal.filtfilt(b, a, data)


def butter_lowpass(highcut, fs, order=3):
    nyq = 0.5 * fs
    high = highcut / nyq
    b, a = signal.butter(order, high, btype="lowpass")
    return b, a
