import re


def prevent_name_collision(name, all_names):
    if name == "":
        name = "1"

    while name in all_names:
        end_digits = get_end_digits(name)
        if end_digits:
            name = end_digits.group(1) + str(int(end_digits.group(2)) + 1)
        else:
            name += "2"
    return name


def get_end_digits(name):
    return re.compile(r"(.*?)(\d+)$").search(name)
