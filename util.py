import os
import logging
import sys
import datetime
from definitions import DATE_FORMAT, DATETIME_FORMAT, LOG_FORMAT, LOG_DIR


def setup_root_logger(level=logging.DEBUG, format_=LOG_FORMAT, stream=sys.stdout, out_dir=LOG_DIR):
    logger = logging.getLogger()
    logger.setLevel(level)
    console_handler = logging.StreamHandler(stream)
    path = os.path.join(out_dir, now_name(".log"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    formatter = logging.Formatter(format_)
    for handler in (console_handler, file_handler):
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def silence_loggers(*names):
    for name in names:
        logger = logging.getLogger(name)
        logger.propagate = False


def datetime_from_name(name):
    name = os.path.basename(name)
    root, _ = os.path.splitext(name)
    fmt = DATETIME_FORMAT if root.count("-") == 4 else DATE_FORMAT
    return datetime.datetime.strptime(root, fmt)


def datetime_to_name(when, ext=None):
    if isinstance(when, datetime.datetime):
        name = when.isoformat(timespec="seconds").replace(":", "-")
    elif isinstance(when, datetime.date):
        name = when.isoformat()
    else:
        raise ValueError("'when' must be datetime.datetime or datetime.date")
    if ext:
        if not ext.startswith("."):
            ext = "." + ext
        name += ext
    return name


def date_from_name(name):
    return datetime_from_name(name).date()


def date_to_name(when, ext=None):
    return datetime_to_name(when, ext=ext)


def now_name(ext=None):
    return datetime_to_name(datetime.datetime.now(), ext=ext)


def today_name(ext=None):
    return date_to_name(datetime.date.today(), ext=ext)
