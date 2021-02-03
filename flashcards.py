import re
import logging
import inspect
import pydoc
import random
from collections import OrderedDict
from type_checking import is_special, is_private, is_deprecated

logger = logging.getLogger(__name__)


def get_doc(obj, short=True):
    doc = pydoc.getdoc(obj)
    if short:
        doc, _ = pydoc.splitdoc(doc)
    return doc if doc else None


def get_sig(obj):
    sig = "()"
    try:
        sig = inspect.signature(obj)
    except ValueError:
        doc = get_doc(obj, short=True)
        if doc:
            match = re.match(r"([\w\.]+)(\(.+\))", doc)
            if match:
                sig = match[2]
                logger.debug("Found signature for %s using fallback.", obj.__name__)
    if sig == "()":
        logger.debug("Could not find signature for %s.", obj.__name__)
    return sig


def create_deck(obj, skip_special=True, skip_private=True, short=True, shuffle=False):
    cards = OrderedDict()
    functions = inspect.getmembers(obj, inspect.isroutine)
    if shuffle:
        random.shuffle(functions)
    for name, func in functions:
        if any((skip_special and is_special(func),
                skip_private and is_private(func),
                is_deprecated(func))):
            continue
        sig = get_sig(func)
        name = f"{obj.__name__}.{name}{sig}"
        doc = get_doc(func, short=short)
        if doc:
            cards[name] = doc
    return cards
