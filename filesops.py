import json
import os


def read_json(filename):
    """
    Read data from a JSON file.
    """

    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(filename, data):
    """
    Write data to a JSON file.
    """

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def find_by_id(filename, key, value):
    """
    Find one record from JSON file.
    """

    data = read_json(filename)

    for item in data:
        if item.get(key) == value:
            return item

    return None