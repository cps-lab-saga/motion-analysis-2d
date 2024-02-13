import json
import re


def load_preferences(path):
    with open(path, "r", encoding="utf-8") as f:
        jsondata = re.sub("//.*", "", f.read(), flags=re.MULTILINE)
        data = json.loads(jsondata)
    return data


def save_preferences(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=False, indent=4)
