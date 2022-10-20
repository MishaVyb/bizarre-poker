from __future__ import annotations

import inspect
import itertools
import logging
import operator
import re
from typing import Any, Callable, Iterable, Sequence, SupportsIndex
from core.utils.types import _SupportsRichComparison


def init_logger(name, level=logging.DEBUG) -> logging.Logger:
    """Get or create default logger by givven name."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger


logger = init_logger(__name__)


def change_loggers_level(level, match_name: str = r'games', exclude_match: str = ''):
    for name in logging.root.manager.loggerDict:
        if re.match(match_name, name):
            if exclude_match and re.match(exclude_match, name):
                continue
            logging.getLogger(name).setLevel(level)


def eq_first(minor: str, major: str, case_sensitive=False) -> bool:
    """
    True if minor string is equivalent to major string from begining.

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
    """
    Extension for default str.split() method.

    Split string by each symbol from delimiter-string and return list of strings.
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
    def purple(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._PURPLE + __str + cls._ENDC

    @classmethod
    def bold(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._BOLD + __str + cls._ENDC

    @classmethod
    def underline(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._UNDERLINE + __str + cls._ENDC

    @classmethod
    def green(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._GREEN + __str + cls._ENDC

    @classmethod
    def blue(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._BLUE + __str + cls._ENDC

    @classmethod
    def cyan(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._CYAN + __str + cls._ENDC

    @classmethod
    def red(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._RED + __str + cls._ENDC

    @classmethod
    def yellow(cls, __str: Any) -> str:
        if not __str:
            return ''
        __str = str(__str)
        return cls._ENDC + cls._YELLOW + __str + cls._ENDC


def is_sorted(
    *sequences: Sequence[_SupportsRichComparison],
    key: str | Callable[[_SupportsRichComparison], Any] | None = None,
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
