import pydoc


def is_special(obj):
    return obj.__name__.startswith("__") and obj.__name__.endswith("__")


def is_private(obj):
    return obj.__name__.startswith("_") and not is_special(obj)


def is_deprecated(obj):
    short, _ = pydoc.splitdoc(pydoc.getdoc(obj))
    return "deprecated" in short.lower()
