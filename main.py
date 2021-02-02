import inspect
import logging
import random
import win_unicode_console
import util
import pydoc

win_unicode_console.streams.enable()
util.setup_root_logger()
logger = logging.getLogger(__name__)

tar = input("Target: ")
obj, tar = pydoc.resolve(tar)
if not (inspect.isclass(obj) or inspect.ismodule(obj)):
    raise TypeError("target must be class or module")


def is_special(name):
    return name.startswith("__") and name.endswith("__")


def is_private(name):
    return name.startswith("_") and not is_special(name)


def is_deprecated(obj):
    short, _ = pydoc.splitdoc(pydoc.getdoc(obj))
    return " deprecated " in short


# def describe(thing, forceload=0):
#     object, name = pydoc.resolve(thing, forceload)
#     desc = pydoc.describe(object)
#     module = inspect.getmodule(object)
#     if name and '.' in name:
#         desc += ' in ' + name[:name.rfind('.')]
#     elif module and module is not object:
#         desc += ' in module ' + module.__name__
#     return f"{name}: {desc}"


cards = dict()

skip_private = True
skip_special = True
short = True

for name, val in inspect.getmembers(obj, inspect.isfunction):
    if skip_special and is_special(name):
        continue
    if skip_private and is_private(name):
        continue
    if is_deprecated(val):
        continue
    doc = pydoc.getdoc(val)
    if short:
        doc, _ = pydoc.splitdoc(doc)
    if doc:
        cards[name] = doc

keys = list(cards.keys())
# random.shuffle(keys)
for key in keys:
    try:
        sig = inspect.signature(getattr(obj, key))
        prompt = f"{tar}.{key}{sig}"
        prompt = pydoc.cram(prompt, 100)
    except ValueError as e:
        logger.debug(e)
        prompt = f"{tar}.{key}()"
        continue
    print("\n"*3)
    # prompt2 = describe(f"{tar}.{key}")
    resp = input(prompt)
    print("-"*len(prompt))
    print(cards[key])
