"""
Utilities.

developing:
[ ] Argument 1 has incompatible type "_TC"; expected "Union[
    _SupportsDunderLE, _SupportsDunderGE, _SupportsDunderGT, _SupportsDunderLT]
"""

from __future__ import annotations

import itertools
import logging
import operator
import re
from typing import Any, Callable, Iterable, Sequence, SupportsIndex, TypeVar, overload


def eq_first(minor: str, major: str, case_sensitive=False) -> bool:
    """True if minor string is equivalent to major string from begining

    >>> eq_first('eq', 'equivalent')
    True
    >>> eq_first('eq', 'not eq')
    False
    """
    if len(minor) > len(major):
        return False
    if not case_sensitive:
        minor = minor.casefold()
        major = major.casefold()
    for l1, l2 in zip(minor, major):
        if l1 != l2:
            return False
    return bool(minor) or (not minor and not major)


def split(
    __str: str,
    by_symbols: str = ' \n,./|()-[]'
) -> list[str]:
    """Split string by each symbol from delimiter-string and return list of strings.
    Empty strings filtered out from result list.
    """
    delimeters_list = list(itertools.chain(*by_symbols))
    splited = re.split('|'.join(map(re.escape, delimeters_list)), __str)
    return list(filter(None, splited))  # filter for removing empty strings


class PrintColors:
    _HEADER = '\033[95m'
    _OKBLUE = '\033[94m'
    _OKCYAN = '\033[96m'
    _OKGREEN = '\033[92m'
    _WARNING = '\033[93m'
    _FAIL = '\033[91m'
    _ENDC = '\033[0m'
    _BOLD = '\033[1m'
    _UNDERLINE = '\033[4m'

    def __init__(self, activated=True) -> None:
        self.activated = activated
        pass

    def __call__(self, *args: Any, **kwds: Any) -> None:
        if self.activated:
            print(*args, **kwds)

    def header(self, *args, **kwargs) -> None:
        self(self._HEADER, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')

    def bold(self, *args, **kwargs) -> None:
        self(self._BOLD, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')

    def underline(self, *args, **kwargs) -> None:
        self(self._UNDERLINE, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')

    def green(self, *args, **kwargs) -> None:
        self(self._OKGREEN, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')

    def fail(self, *args, **kwargs) -> None:
        self(self._FAIL, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')

    def warning(self, *args, **kwargs) -> None:
        self(self._WARNING, end='')
        self(*args, **kwargs)
        self(self._ENDC, end='')


print_colors = PrintColors()

_TC = TypeVar('_TC')


def is_sorted(
    *sequences: Sequence[_TC],
    key: str | Callable[[_TC], Any] | None = None,
    reverse: bool = False,
) -> bool:
    # comparisons operator
    compr = operator.ge if reverse else operator.le

    if not key:
        for sequence in sequences:
            if not all(
                compr(sequence[i], sequence[i + 1])  # type: ignore
                for i in range(len(sequence) - 1)
            ):
                return False
    elif isinstance(key, str):
        for sequence in sequences:
            if not all(
                compr(getattr(sequence[i], key), getattr(sequence[i + 1], key))
                for i in range(len(sequence) - 1)
            ):
                return False
    elif callable(key):
        for sequence in sequences:
            if not all(
                compr(key(sequence[i]), key(sequence[i + 1]))
                for i in range(len(sequence) - 1)
            ):
                return False
    else:
        raise TypeError

    return True


def range_inclusevly(
    __start: SupportsIndex = 0, __stop: SupportsIndex = None, __step: SupportsIndex = 1
) -> range:
    if isinstance(__stop, int):
        return range(__start, __stop + 1, __step)
    raise NotImplementedError


def isinstance_items(container: Iterable, container_type: type, item_type: type):
    return isinstance(container, container_type) and all(
        map(lambda x: isinstance(x, item_type), container)
    )


def init_logger(name, level=logging.DEBUG) -> logging.Logger:
    """Get or create default logger by givven name."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            '%(levelname)s - %(name)s - %(funcName)s - %(lineno)d - %(message)s'
        )
    )
    logger.addHandler(handler)
    return logger