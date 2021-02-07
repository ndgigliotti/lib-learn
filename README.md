# lib-learn

A CLI flashcard simulator for learning the routines of Python libraries.

Explore a new library or delve into a familiar one. Discover functions you never knew existed.

## Usage
Run the script with the target class or module as the sole positional argument. You must provide the dotted path, like those used in `import` statements.

```shell
python main.py pandas.DataFrame
```

The output is the path and signature of the first routine&mdash;the front of the first flashcard in the deck. The deck is sorted alphabetically by default.

```
pandas.DataFrame.abs(self:~FrameOrSeries) -> ~FrameOrSeries_
```

Press <kbd>Enter</kbd> to view the back of the card.

```
pandas.DataFrame.abs(self:~FrameOrSeries) -> ~FrameOrSeries
-----------------------------------------------------------
Return a Series/DataFrame with absolute numeric value of each element._
```

>By default, the back contains the synopsis line of the routine's docstring. For some libraries&mdash;especially those with unorthodox docstring formatting&mdash;this may not be useful. Use `-f` to show full docstrings.

Press <kbd>Enter</kbd> again to proceed to the next card.

```
pandas.DataFrame.add(self, other, axis='columns', level=None, fill_value=None)_
```

You can continue iterating through the cards by pressing <kbd>Enter</kbd> until you reach the end of the deck.

## Optional Flags

|        Flag         |             Effect             |
| ------------------- | ------------------------------ |
| `-h`, `--help`      | Show help message and exit.    |
| `-f`, `--full`      | Show full-length docstrings.   |
| `-c`, `--cycle`     | Cycle the deck indefinitely.   |
| `-s`, `--shuffle`   | Keep the deck shuffled.        |
| `-pr`, `--private`  | Allow `_private` routines.     |
| `-sp`, `--special`  | Allow `__special__` routines.  |

## Known Issues

- Cannot obtain signatures for some routines using `inspect.signature`.
  - Unresolved: which ones exactly and why?
  - Fallback works on `numpy.ndarray` class. Does it work on anything else?
- Does not work on `itertools` module. Why?

## Todo
- [x] Add cycle feature
- [ ] Add commands to get further details on routines
- [ ] Investigate known issues
- [ ] Complete docstrings
- [ ] Allow class flashcards
- [ ] Develop mass-library test

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
