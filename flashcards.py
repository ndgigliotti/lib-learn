import re
import logging
import inspect
import json
import pydoc
import random
from collections import OrderedDict
from type_checking import is_special, is_private, is_deprecated
import util

logger = logging.getLogger(__name__)


def get_path(obj):
    if hasattr(obj, "__module__"):
        return f"{obj.__module__}.{obj.__name__}"
    return obj.__name__


def _sig_fallback(obj, parent, syn, rem, short=True):
    """
    Look for the signature in the synopsis line.

    Check if the synopsis line is a signature and extract it if so. Ensure that
    the extracted signature has the `self` parameter if `parent` is a class.
    Retrieve a new synopsis line from the remaining docstring if appropriate.

    Args:
        obj (routine): The routine in need of a signature.
        parent (class): Parent class or module of `obj`.
        syn (str): Synopsis line of the `obj` docstring.
        rem (str): Remainder of the `obj` docstring.
        short (:obj:`bool`, optional): Just get the synopsis line. True by default.
    Returns:
        tuple: (signature, docstring)

    """
    path = get_path(obj)
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
        logger.debug("Found signature for `%s` using fallback.", path)
    else:
        if short:
            results = (None, syn)
        else:
            results = (None, "\n".join((syn, rem)))
        logger.debug("Could not find signature for `%s`.", path)
    return results


def get_doc(obj, parent, short=True):
    """
    Get the signature and docstring of the given object.

    Args:
        obj (routine): Function, method, methoddescriptor, or builtin.
        parent (class): Parent class or module of `obj`.
        short (:obj:`bool`, optional): Just get the synopsis line. True by default.

    Returns:
        tuple: (signature, docstring)

    """
    doc = pydoc.getdoc(obj)
    syn, rem = pydoc.splitdoc(doc)
    path = get_path(obj)
    try:
        sig = inspect.signature(obj)
        logger.debug("Found signature for `%s` using inspect.", path)
    except ValueError:
        return _sig_fallback(obj, parent, syn, rem, short=short)
    if short:
        return (sig, syn)
    return (sig, doc)


def create_deck(path, allow_special=False, allow_private=False, short=True, shuffle=False):
    """
    Create a "flashcard deck" of the target class or module's routines.

    Construct an ordered mapping of routine names to docstrings for the target
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
    logger.debug("Looking for documentation: `%s`", path)
    cards = OrderedDict()
    obj, _ = pydoc.resolve(path)
    if not (inspect.isclass(obj) or inspect.ismodule(obj)):
        raise TypeError("target must be class or module")
    functions = inspect.getmembers(obj, inspect.isroutine)
    if shuffle:
        random.shuffle(functions)
    n_eligible = 0
    for name, func in functions:
        if any((not allow_special and is_special(func),
                not allow_private and is_private(func),
                is_deprecated(func))):
            continue
        sig, doc = get_doc(func, obj, short=short)
        n_eligible += 1
        if sig and doc:
            cards[f"{path}.{name}{sig}"] = doc
        elif not doc:
            logger.debug("Could not find docstring for `%s.%s`.", path, name)
    logger.debug("Finished looking for documentation.")
    logger.debug("Found documentation for %i / %i eligible routines.",
                 len(cards), n_eligible)
    return cards


def prompt_cards(cards, cycle=False, shuffle=False):
    names = cards.keys()
    if cycle:
        names = util.cycle(names, shuffle_bet=shuffle)

    for name in names:
        print("\n"*3)
        input(name)
        print("-"*len(name))
        input(cards[name])


def log_deck(path, deck):
    logger.debug("\n")
    logger.debug("Deck: `%s` Length: %i", path, len(deck))
    logger.debug(json.dumps(deck))
    logger.debug("\n")
