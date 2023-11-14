import json
import re


def load_application_settings(path):
    with open(path, "r", encoding="utf-8") as f:
        jsondata = re.sub("//.*", "", f.read(), flags=re.MULTILINE)
        data = json.loads(jsondata)
    return data
