import inspect
import logging
import pydoc
import random
import win_unicode_console
import util
import flashcards


SKIP_PRIVATE = True
SKIP_SPECIAL = True
SHORT = False
SHUFFLE = False

win_unicode_console.streams.enable()
util.setup_root_logger()
logger = logging.getLogger(__name__)

tar_name = input("Enter target: ")
tar_object, tar_name = pydoc.resolve(tar_name)
if not (inspect.isclass(tar_object) or inspect.ismodule(tar_object)):
    raise TypeError("target must be class or module")


cards = flashcards.create_deck(tar_object,
                               skip_private=SKIP_PRIVATE,
                               skip_special=SKIP_SPECIAL,
                               short=SHORT,
                               shuffle=SHUFFLE)

for name in cards:
    print("\n"*3)
    # prompt2 = describe(f"{tar}.{key}")
    resp = input(name)
    print("-"*len(name))
    print(cards[name])
