import mimetypes

mimetypes.init()


def guess_file_type(file_path):
    return mimetypes.guess_type(file_path)[0]


def check_file_type(file_path, file_types):
    if guessed_type := guess_file_type(file_path):
        return guessed_type.split("/")[0] in file_types


def is_json_file(file_path):
    if file_type := guess_file_type(file_path):
        return file_type == "application/json"
