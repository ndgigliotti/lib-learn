import logging
import argparse
from collections import OrderedDict
import win_unicode_console
import util
import flashcards
from definitions import STDLIB

win_unicode_console.streams.enable()
util.setup_root_logger()
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Run tests of lib-learn.")
parser.add_argument("--path", help="path of target class or module", default=None)
parser.add_argument("--file", help="text file listing targets", default=None)
parser.add_argument("-f", "--full", help="show full-length docstrings", action="store_true")
parser.add_argument("-pr", "--private", help="allow private routines", action="store_true")
parser.add_argument("-sp", "--special", help="allow special routines", action="store_true")
args = parser.parse_args()

paths = []

if args.path is not None:
    paths.append(args.path)
elif args.file is not None:
    with open(args.file) as f:
        paths = f.read().split("\n")
        paths = list(filter(None, paths))
else:
    paths = STDLIB

results = dict()
for path in paths:
    try:
        deck, quality = flashcards.create_deck(path,
                                               allow_private=args.private,
                                               allow_special=args.special,
                                               short=not args.full)
    except Exception as e:
        logger.error(e)
        results[path] = -100
        continue
    flashcards.log_deck(path, deck, quality)
    results[path] = quality

results = OrderedDict(sorted(results.items(), key=lambda x: x[1]))
logger.info("\n")
logger.info("Results")
logger.info("-------")
for path in results:
    logger.info("%s: %.2f", path, round(results[path], 2))
