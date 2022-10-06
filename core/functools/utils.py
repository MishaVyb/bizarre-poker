"""
Utilities.
"""

from __future__ import annotations
from abc import ABCMeta, abstractmethod
import inspect

import itertools
import logging
import operator
import re
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    Sequence,
    SupportsIndex,
    TypeVar,
    Generic,
)


def init_logger(name, level=logging.DEBUG) -> logging.Logger:
    """Get or create default logger by givven name."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            # '%(levelname)s - %(name)s - %(funcName)s - %(lineno)d - %(message)s'
            '%(levelname)s - %(message)s'
        )
    )
    logger.addHandler(handler)
    return logger


logger = init_logger(__name__)


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


def split(__str: str, by_symbols: str = ' \n,./|()-[]') -> list[str]:
    """Split string by each symbol from delimiter-string and return list of strings.
    Empty strings filtered out from result list.
    """
    delimeters_list = list(itertools.chain(*by_symbols))
    splited = re.split('|'.join(map(re.escape, delimeters_list)), __str)
    return list(filter(None, splited))  # filter for removing empty strings


class StrColors:
    _PURPLE = '\033[95m'
    _BLUE = '\033[94m'
    _CYAN = '\033[96m'
    _GREEN = '\033[92m'
    _YELLOW = '\033[93m'
    _RED = '\033[91m'
    _ENDC = '\033[0m'
    _BOLD = '\033[1m'
    _UNDERLINE = '\033[4m'

    @classmethod
    def purple(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._PURPLE + __str + cls._ENDC

    @classmethod
    def bold(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._BOLD + __str + cls._ENDC

    @classmethod
    def underline(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._UNDERLINE + __str + cls._ENDC

    @classmethod
    def green(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._GREEN + __str + cls._ENDC

    @classmethod
    def blue(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._BLUE + __str + cls._ENDC

    @classmethod
    def cyan(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._CYAN + __str + cls._ENDC

    @classmethod
    def red(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._RED + __str + cls._ENDC

    @classmethod
    def yellow(cls, __str: str) -> str:
        __str = str(__str)
        return cls._ENDC + cls._YELLOW + __str + cls._ENDC


class Comparable(metaclass=ABCMeta):
    @abstractmethod
    def __lt__(self, other: Any) -> bool:
        ...


class TotalComparable(metaclass=ABCMeta):
    @abstractmethod
    def __lt__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __le__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __ne__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __ge__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __gt__(self, other: Any) -> bool:
        ...


_CT = TypeVar('_CT', bound=Comparable)  # _CT -- compariable type
_TCT = TypeVar('_TCT', bound=TotalComparable)  # _TCT -- total compariable type


def is_sorted(
    *sequences: Sequence[_CT],
    key: str | Callable[[_CT], Any] | None = None,
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


def change_loggers_level(level, match_name: str = r'games', exclude_match: str = ''):
    for name in logging.root.manager.loggerDict:
        if re.match(match_name, name):
            if exclude_match and re.match(exclude_match, name):
                continue
            logging.getLogger(name).setLevel(level)


def get_func_name(back=False) -> str:
    frame = inspect.currentframe()

    # single back
    if not back:
        if not frame or not frame.f_back:
            return 'no_func_name'
        return frame.f_back.f_code.co_name

    # double back
    if not frame or not frame.f_back or not frame.f_back.f_back:
        return 'no_func_name'
    return frame.f_back.f_back.f_code.co_name


def reverse_attrgetter(*attrs: str):
    return lambda x: not bool(operator.attrgetter(*attrs)(x))


class Interval(Generic[_TCT]):
    """
    Interval represents value range (both max and min inclusevly).

    >>> 12 in Interval(10, 20)
    True
    >>> 20 in Interval(10, 20)  # inclusevly 20
    True
    >>> 0.1 in Interval(0.11, 1)
    False

    """

    def __init__(self, min_: _TCT, max_: _TCT) -> None:
        self.min = min_
        self.max = max_
        self._check_constraints()

    def __repr__(self) -> str:
        return f'[{self.min}]->[{self.max}]'

    def __getitem__(self, index: Literal[0, 1]) -> _TCT:
        if index not in [0, 1]:
            raise IndexError
        return self.max if index else self.min

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Interval):
            return (self.min, self.max) == (other.min, other.max)
        return NotImplemented

    def __contains__(self, items: _TCT | Iterable[_TCT]):
        self._check_constraints()
        if not isinstance(items, Iterable):
            items = [items]

        return all(self.min <= item <= self.max for item in items)

    def _check_constraints(self):
        if not self.min <= self.max:
            raise ValueError('Invalid interval with min > max. ')
        elif self.min == self.max:
            logger.warning('Iterval with min == max. That`s how it should be?')
