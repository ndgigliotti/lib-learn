import logging
import argparse
import win_unicode_console
import util
import flashcards

win_unicode_console.streams.enable()
util.setup_root_logger()
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Learn the routines of a class or module.")
parser.add_argument("path")
parser.add_argument("-f", "--full", help="show full-length docstrings", action="store_true")
parser.add_argument("-s", "--shuffle",  help="shuffle the routines", action="store_true")
parser.add_argument("-pr", "--private", help="allow private routines", action="store_true")
parser.add_argument("-sp", "--special", help="allow special routines", action="store_true")
args = parser.parse_args()

cards = flashcards.create_deck(args.path,
                               allow_private=args.private,
                               allow_special=args.special,
                               short=not args.full,
                               shuffle=args.shuffle)

for name in cards:
    print("\n"*3)
    resp = input(name)
    print("-"*len(name))
    print(cards[name])
