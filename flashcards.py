import re
import logging
import inspect
import pydoc
import random
from collections import OrderedDict
from type_checking import is_special, is_private, is_deprecated

logger = logging.getLogger(__name__)


def _sig_fallback(name, syn, rem, short=True, parent=None):
    match = re.match(r"([\w\.]+)\((.*)\)", syn)
    if match:
        sig = match[2]
        if inspect.isclass(parent):
            if sig and not sig.startswith("self"):
                sig = f"self, {sig}"
            elif not sig.startswith("self"):
                sig = "self"
        sig = f"({sig})"
        if short:
            syn2, _ = pydoc.splitdoc(rem)
            results = (sig, syn2)
        else:
            results = (sig, rem)
        logger.debug("Found signature for %s using fallback.", name)
    else:
        results = (None, None)
        logger.debug("Could not find signature for %s.", name)
    return results


def get_doc(obj, short=True, parent=None):
    doc = pydoc.getdoc(obj)
    syn, rem = pydoc.splitdoc(doc)
    try:
        sig = inspect.signature(obj)
    except ValueError:
        return _sig_fallback(obj.__name__, syn, rem, short=short, parent=parent)
    if short:
        return (sig, syn)
    return (sig, doc)


def create_deck(path, allow_special=False, allow_private=False, short=True, shuffle=False):
    cards = OrderedDict()
    obj, _ = pydoc.resolve(path)
    if not (inspect.isclass(obj) or inspect.ismodule(obj)):
        raise TypeError("target must be class or module")
    functions = inspect.getmembers(obj, inspect.isroutine)
    if shuffle:
        random.shuffle(functions)
    for name, func in functions:
        if any((not allow_special and is_special(func),
                not allow_private and is_private(func),
                is_deprecated(func))):
            continue
        sig, doc = get_doc(func, short=short, parent=obj)
        if sig and doc:
            cards[f"{path}.{name}{sig}"] = doc
    return cards
