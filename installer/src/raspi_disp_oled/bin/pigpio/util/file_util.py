import json


def read_json(file):
    with open(file) as fp:
        data = json.load(fp)
    return data


def save_json(file, jsonobj, indent=4):
    with open(file, "w") as fp:
        json.dump(jsonobj, fp, ensure_ascii=False, indent=indent)


def read_text(file):
    datas = []
    with open(file) as fp:
        for line in fp.readlines():
            datas.append(line)
    return datas


def save_text(file, contents):
    with open(file, 'w') as fp:
        fp.write(contents)
