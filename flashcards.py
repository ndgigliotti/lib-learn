import re
import logging
import inspect
import pydoc
import random
from collections import OrderedDict
from type_checking import is_special, is_private, is_deprecated

logger = logging.getLogger(__name__)


def _sig_fallback(name, syn, rem, short=True, parent=None):
    """Look for the signature in the synopsis line."""
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
        if short:
            results = (None, syn)
        else:
            results = (None, "\n".join((syn, rem)))
        logger.debug("Could not find signature for %s.", name)
    return results


def get_doc(obj, short=True, parent=None):
    """
    Get the signature and docstring of the given object.

    Args:
        obj (routine): Function, method, methoddescriptor, or builtin.
        short (:obj:`bool`, optional): Just get the synopsis line. True by default.
        parent(:obj:`class`, optional): Parent class or module of `obj`. Defaults to None.
            Only used if signature must be obtained by fallback.
    Returns:
        tuple: (signature, docstring)

    """
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
    """
    Create a "flashcard deck" of the target class or module's routines.

    Constructs an ordered mapping of routine names to docstrings for the target
    class or module at `path`. Each routine name is complete with the routine's
    signature.

    Args:
        obj (str): Dotted path to class or module.
        allow_special (:obj:`bool`, optional): Allow __special__ routines. False by default.
        allow_private (:obj:`bool`, optional): Allow _private routines. False by default.
        short (:obj:`bool`, optional): Just get the synopsis line. True by default.
        shuffle(:obj:`bool`, optional): Shuffle the deck.

    Returns:
        OrderedDict: An ordered mapping of routine names to docstrings.

    Raises:
        TypeError: If `path` resolves to anything other than a class or module.
        ImportError: If no documentation can be found at `path`.

    """
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
