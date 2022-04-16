import json


def read_json(file):
    with open(file) as fp:
        data = json.load(fp)
    return data


def save_text(file, contents):
    with open(file, 'w') as fp:
        fp.write(contents)
