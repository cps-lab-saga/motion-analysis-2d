import pytest

from motion_analysis_2d.funcs.check_mimetypes import guess_file_type, check_file_type

guess_file_type_testdata = [
    ("a.jpg", "image/jpeg"),
    ("a.mp4", "video/mp4"),
    ("a.json", "application/json"),
]

check_file_type_testdata = [
    ("a.jpg", ["image"], True),
    ("a.mp4", ["video"], True),
    ("a.mp4", ["application"], False),
    ("a.json", ["application"], True),
]


@pytest.mark.parametrize("file_name, expected", guess_file_type_testdata)
def test_guess_file_type(file_name, expected):
    assert guess_file_type(file_name) == expected


@pytest.mark.parametrize("file_name, file_types, expected", check_file_type_testdata)
def test_check_file_type(file_name, file_types, expected):
    assert check_file_type(file_name, file_types) == expected
