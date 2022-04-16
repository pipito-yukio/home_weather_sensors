import os
from pathlib import Path
from datetime import datetime
import logging
import logging.config
import json

__instance = None


def create_logger(app_name, path_log_conf, path_logs):
    print("create_logger(app_name:{})".format(app_name))
    global __instance
    if __instance is None:
        _init("logconf_{}.json".format(app_name), path_log_conf, path_logs)
        __instance = object()
    return logging.getLogger(app_name)


def get_logger(name):
    print("get_logger({})".format(name))
    return logging.getLogger(name)


def _init(logconf_name, path_log_conf, path_app_logs):
    logconf_file = os.path.join(path_log_conf, logconf_name)
    with open(logconf_file) as fp:
        logconf = json.load(fp)
    fmt_filename = logconf['handlers']['fileHandler']['filename']
    # "filename": "{}/xxxxxxx.log"
    filename = fmt_filename.format(path_app_logs)
    fullpath = os.path.expanduser(filename)
    logdir = Path(os.path.dirname(fullpath))
    if not logdir.exists():
        logdir.mkdir(parents=True)

    base, extension = os.path.splitext(fullpath)
    datepart = datetime.now().strftime("%Y%m%d%H%M")
    filename = "{}_{}{}".format(base, datepart, extension)
    print("logFile:{}".format(filename))
    # Override
    logconf['handlers']['fileHandler']['filename'] = filename
    logging.config.dictConfig(logconf)
