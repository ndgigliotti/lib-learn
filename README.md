# lib-learn
A CLI flashcard simulator for learning the functions of Python libraries.

Explore a new library or delve into a familiar one. Discover functions you never knew existed.

## Usage
Run the program with the target class or module as the sole positional argument. You must provide the dotted path, like those used in `import` statements.

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
Return a Series/DataFrame with absolute numeric value of each element.
_
```

>By default, the back contains the synopsis line of the routine's docstring. For some libraries&mdash;especially those with unorthodox docstring formatting&mdash;this may not be useful. Use `-f` to show full docstrings.

Press <kbd>Enter</kbd> again to proceed to the next card.

```
pandas.DataFrame.add(self, other, axis='columns', level=None, fill_value=None)_
```

You can continue iterating through the cards by pressing <kbd>Enter</kbd>.

## Optional Flags
|        Flag         |             Effect             |
| ------------------- | ------------------------------ |
| `-h`, `--help`      | Show help message and exit.    |
| `-f`, `--full`      | Show full-length docstrings.   |
| `-c`, `--cycle`     | Cycle the deck indefinitely.   |
| `-s`, `--shuffle`   | Keep the deck shuffled.        |
| `-p`, `--private`   | Allow `_private` routines.     |
| `-m`, `--special`   | Allow `__special__` routines.  |

## Known Issues
- Cannot obtain signatures for some routines using `inspect.signature`.
  - Which ones exactly and why?
- Does not work on `itertools` module.
  - Apparent functions are actually classes.

## Todo
- [x] Add cycle feature
- [x] Develop broad library sweep
- [ ] Develop log analysis tools
- [ ] Add commands to get further details on routines
- [ ] Add quit command
- [ ] Investigate known issues
- [ ] Complete docstrings


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please be sure to update the test.

## License
[MIT](https://choosealicense.com/licenses/mit/)
