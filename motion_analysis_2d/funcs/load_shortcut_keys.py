import json
import re


def load_shortcut_keys(path):
    with open(path, "r", encoding="utf-8") as f:
        jsondata = re.sub("//.*", "", f.read(), flags=re.MULTILINE)
        shortcut_keys = json.loads(jsondata)
    return shortcut_keys
