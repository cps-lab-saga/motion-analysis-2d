import pytest

from motion_analysis_2d.funcs.naming import prevent_name_collision

current_names = [
    "test1",
    "test2",
    "test9",
    "test11",
    "test22",
    "test29",
    "test99",
    "test111",
    "test222",
]

testdata = [
    ("test", current_names, "test"),
    ("test1", current_names, "test3"),
    ("test2", current_names, "test3"),
    ("test3", current_names, "test3"),
    ("test9", current_names, "test10"),
    ("test10", current_names, "test10"),
    ("test11", current_names, "test12"),
    ("test22", current_names, "test23"),
    ("test29", current_names, "test30"),
    ("test99", current_names, "test100"),
]


@pytest.mark.parametrize("name, all_names, expected", testdata)
def test_prevent_name_collision(name, all_names, expected):
    assert prevent_name_collision(name, all_names) == expected
