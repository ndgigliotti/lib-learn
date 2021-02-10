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


def get_path(parent, child):
    """Return the dotted path of `child` relative to its parent class or module."""
    return f"{parent.__name__}.{child.__name__}"


def _sig_fallback(obj, parent, doc):
    """
    Look for the signature in the synopsis line.

    Check if the synopsis line is a signature and extract it if so. Ensure that
    the extracted signature has the `self` parameter if `parent` is a class.

    Args:
        obj (routine): Routine in need of signature.
        parent (class): Parent class or module of `obj`.
        doc (str): Docstring of `obj`.
    Returns:
        tuple: (signature, docstring)

    """
    path = get_path(parent, obj)
    syn, rem = pydoc.splitdoc(doc)
    match = re.match(r"([\w\.]+)\((.*)\)", syn)
    if match:
        sig = match[2]
        if inspect.isclass(parent):
            if sig and not sig.startswith("self"):
                sig = f"self, {sig}"
            elif not sig.startswith("self"):
                sig = "self"
        sig = f"({sig})"
        results = (sig, rem)
        logger.debug("Found signature for `%s` using fallback.", path)
    else:
        results = ("(...)", "\n".join((syn, rem)))
        logger.debug("Could not find signature for `%s`.", path)
    return results


def get_doc(obj, parent):
    """
    Get the signature and docstring of the given object.

    Args:
        obj (routine): Function, method, methoddescriptor, or builtin.
        parent (class): Parent class or module of `obj`.

    Returns:
        tuple: (signature, docstring)

    """
    doc = pydoc.getdoc(obj)
    path = get_path(parent, obj)
    try:
        sig = inspect.signature(obj)
        results = (sig, doc)
        logger.debug("Found signature for `%s` using inspect.", path)
    except ValueError:
        results = _sig_fallback(obj, parent, doc)
    if not doc:
        logger.debug("Could not find docstring for `%s`.", path)
    return results


def try_shorten(doc):
    """Return the synopsis line if available, otherwise `doc`."""
    syn, _ = pydoc.splitdoc(doc)
    if syn:
        return syn
    logger.debug("\n")
    logger.debug("Could not shorten docstring:")
    logger.debug(repr(doc))
    logger.debug("\n")
    return doc


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
        short (:obj:`bool`, optional): Try to get only the synopsis line. True by default.
        shuffle(:obj:`bool`, optional): Shuffle the deck.

    Returns:
        tuple: (cards, quality)

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
        sig, doc = get_doc(func, obj)
        n_eligible += 1
        if doc:
            cards[f"{path}.{name}{sig}"] = try_shorten(doc) if short else doc
    logger.debug("Finished looking for documentation.")
    quality = (len(cards) / n_eligible) * 100
    logger.debug("Found documentation for %i / %i (%i%%) eligible routines.",
                 len(cards), n_eligible, round(quality))
    return cards, quality


def prompt_cards(cards, cycle=False, shuffle=False):
    names = cards.keys()
    if cycle:
        names = util.cycle(names, shuffle_bet=shuffle)

    for name in names:
        print("\n"*3)
        input(name)
        print("-"*len(name))
        input(cards[name])


def log_deck(path, deck, quality):
    logger.debug("\n")
    logger.debug("Deck: `%s`, Length: %i, Quality: %.2f%%",
                 path, len(deck), round(quality, 2))
    logger.debug(json.dumps(deck))
    logger.debug("\n")
