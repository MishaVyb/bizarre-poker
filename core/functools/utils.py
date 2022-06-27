"""
Utilities.

developing:
[ ] Argument 1 has incompatible type "_TC"; expected "Union[
    _SupportsDunderLE, _SupportsDunderGE, _SupportsDunderGT, _SupportsDunderLT]
"""

from __future__ import annotations

import itertools
import operator
import re
from typing import Any, Callable, Iterable, Sequence, SupportsIndex, TypeVar, overload


def eq_first(minor: str, major: str, case_sensitive=False) -> bool:
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
    by_symbols: str = ' \n,./|()-[]',
    by_delimeters: list[str] = None,
    exclude_delimeters: str = None,
) -> list[str]:
    """Split string by each symbol from delimiter-string and return list of strings.
    Empty strings filtered out from result list.
    """
    assert not exclude_delimeters, 'not implemented yet'
    assert not by_delimeters, 'not implemented yet'

    delimeters_list = list(itertools.chain(*by_symbols))
    splited = re.split('|'.join(map(re.escape, delimeters_list)), __str)
    return list(filter(None, splited))  # filter for removing "" empty string


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

    def __call__(self, *args: Any, **kwds: Any) -> None:
        print(*args, **kwds)
        pass

    @classmethod
    def header(cls, *args, **kwargs) -> None:
        print(cls._HEADER, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')

    @classmethod
    def bold(cls, *args, **kwargs) -> None:
        print(cls._BOLD, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')

    @classmethod
    def underline(cls, *args, **kwargs) -> None:
        print(cls._UNDERLINE, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')

    @classmethod
    def green(cls, *args, **kwargs) -> None:
        print(cls._OKGREEN, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')

    @classmethod
    def fail(cls, *args, **kwargs) -> None:
        print(cls._FAIL, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')

    @classmethod
    def warning(cls, *args, **kwargs) -> None:
        print(cls._WARNING, end='')
        print(*args, **kwargs)
        print(cls._ENDC, end='')


print_colors = PrintColors()  # default instance for easy access

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
                compr(sequence[i], sequence[i + 1]) for i in range(len(sequence) - 1)
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


@overload
def range_inclusevly(__stop: SupportsIndex, /) -> range:
    ...


@overload
def range_inclusevly(
    __start: SupportsIndex, __stop: SupportsIndex, __step: SupportsIndex = ..., /
) -> range:
    ...


def range_inclusevly(
    __start: SupportsIndex = 0, __stop: SupportsIndex = None, __step: SupportsIndex = 1
) -> range:
    if isinstance(__stop, int):
        return range(__start, __stop + 1, __step)
    raise NotImplementedError


def isinstance_items(__iterable: Iterable, __item_type: type):
    return isinstance(__iterable, Iterable) and all(
        map(lambda x: isinstance(x, __item_type), __iterable)
    )
