import numpy as np
import pytest
from scipy import fft

from motion_analysis_2d.funcs.motion_funcs import (
    angle_vec,
    angle_between,
    filter_lowpass,
)

angle_vec_testdata = [
    (np.array([[1.0, 0.0]]), np.array([0.0])),
    (np.array([[0.0, -1.0]]), np.array([90.0])),
    (np.array([[-1.0, 0.0]]), np.array([180.0])),
    (np.array([[0.0, 1.0]]), np.array([-90.0])),
    (np.array([[1.0, -1.0]]), np.array([45.0])),
    (np.array([[-1.0, -1.0]]), np.array([135.0])),
    (np.array([[-1.0, 1.0]]), np.array([-135.0])),
    (np.array([[1.0, 1.0]]), np.array([-45.0])),
    (np.array([[1.0, 1.0], [2.0, 2.0]]), np.array([-45.0, -45.0])),
]


@pytest.mark.parametrize("vec1, expected", angle_vec_testdata)
def test_angle_vec(vec1, expected):
    angle = angle_vec(vec1)
    assert np.allclose(angle, expected)


angle_between_testdata = [
    (np.array([[1.0, 0.0]]), np.array([[1.0, 0.0]]), np.array([0.0])),
    (np.array([[-1.0, -1.0]]), np.array([[1.0, -1.0]]), np.array([90.0])),
    (np.array([[1.0, -1.0]]), np.array([[-1.0, -1.0]]), np.array([-90.0])),
    (np.array([[1.0, 0.0]]), np.array([[-1.0, -1.0]]), np.array([-135])),
]


@pytest.mark.parametrize("vec1, vec2, expected", angle_between_testdata)
def test_angle_between(vec1, vec2, expected):
    angle = angle_between(vec1, vec2)
    assert np.allclose(angle, expected)


def test_filter_lowpass():
    number_of_samples = 10000
    sampling_period = 0.001
    mag1, freq1 = 5, 2.0
    mag2, freq2 = 2, 60.0
    t = np.linspace(
        0.0, number_of_samples * sampling_period, number_of_samples, endpoint=False
    )
    y = mag1 * np.sin(2 * np.pi * freq1 * t) + mag2 * np.sin(2 * np.pi * freq2 * t)

    y_filtered = filter_lowpass(y, 1 / sampling_period, 8)
    xf = fft.fftfreq(number_of_samples, sampling_period)[: number_of_samples // 2]
    yf_filtered = (
        2 / number_of_samples * np.abs(fft.fft(y_filtered)[0 : number_of_samples // 2])
    )

    assert (xf[xf > 8][yf_filtered[xf > 8] < 0.01]).all()
