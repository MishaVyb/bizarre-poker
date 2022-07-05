"""

developing:
[ ] doc test -- not working
[ ] exclude additional imports
[X] pytest
"""
import functools
from operator import getitem, setitem
from typing import Any

import wrapt

from core.functools.looptools import looptools


class _TemporaryContext:
    def __init__(self, source: dict[str, Any] | type | None = None, **redefenitions):
        self.source = globals() if source is None else source

        self.redefenitions = redefenitions
        self.fields: dict[str, Any] = {}
        """dict contains a `field` we-want-to-redefine per key"""
        self.values: dict[str, Any] = {}
        """dict contains a `value` of field we-want-to-redefine per key"""

    def __enter__(self):
        def _get(dict_or_type, attr_or_item):
            method = getitem if isinstance(dict_or_type, dict) else getattr
            return method(dict_or_type, attr_or_item)

        def _set(dict_or_type, attr_or_item, value):
            method = setitem if isinstance(dict_or_type, dict) else setattr
            method(dict_or_type, attr_or_item, value)

        for key in self.redefenitions:
            attrs = key.split('__')
            for attr, loop in looptools.item(attrs):
                # first iteration:
                try:
                    if loop.single:
                        self.values[key] = _get(self.source, *attrs)
                        _set(self.source, *attrs, self.redefenitions[key])
                        continue
                    elif loop.begins:
                        self.fields[key] = _get(self.source, attr)
                        continue
                except KeyError or AttributeError as e:
                    raise ValueError(
                        f'Invalid {attr} for {self.source}. '
                        f'Are you shure source has such attr? '
                        'If definition of global at another module than decorator is '
                        'calling, you should import it before. ',
                        e,
                    )
                # second and further iterations:
                try:
                    if loop.final:
                        self.values[key] = _get(self.fields[key], attr)
                        _set(self.fields[key], attr, self.redefenitions[key])
                    else:
                        self.fields[key] = _get(self.fields[key], attr)
                except KeyError or AttributeError as e:
                    raise ValueError(f'Invalid attribute: {".".join(attrs)}: ', e)
        return self

    def __exit__(self, *args):
        def _set(dict_or_type, attr_or_item, value):
            method = setitem if isinstance(dict_or_type, dict) else setattr
            method(dict_or_type, attr_or_item, value)

        for key in self.redefenitions:
            attrs = key.split('__')
            attr = attrs[-1]

            if len(attrs) == 1:
                _set(self.source, attr, self.values[key])
            else:
                setattr(self.fields[key], attr, self.values[key])

    def __call__(self, wrapped):
        @functools.wraps(wrapped=wrapped)
        def wrapper(*args, **kwargs):
            self.__enter__()
            result = wrapped(*args, **kwargs)
            self.__exit__()
            return result

        return wrapper


def temporary_globals(
    __globals: dict[str, Any] | type | None = None, **__redefenitions
):
    """Temporary redefenitions for global variables.
    Use bult-in `globals()` method to get global variables.
    """
    # """
    # >>> GLOBAL = 'default'
    # >>> @temporary_globals(GLOBAL='new value')
    # >>> def fun()
    # ...     GLOBAL
    # 'new value'
    # ...
    # >>> GLOBAL
    # 'default'
    # """

    @wrapt.decorator  # also work as functools.wraps
    def wrapper(wrapped, instance, args, kwargs):
        if isinstance(__globals, type):
            data = __globals.__dict__
        elif isinstance(__globals, dict):
            data = __globals
        elif __globals is None:
            data = globals()
        else:
            raise TypeError

        field: dict[str, Any] = {}
        temporary: dict[str, Any] = {}
        for key in __redefenitions:
            attrs = key.split('__')
            try:
                temporary[key] = data[attrs[0]]
                field[key] = data[attrs[0]]
            except KeyError as e:
                raise ValueError(
                    f'Not sopported attribute: {".".join(attrs)}: '
                    f'Are you shure globals() has {attrs[0]}? '
                    'If definition of global at another module than decorator is '
                    'calling, you should import it before. ',
                    e,
                )
            try:
                for attr, loop in looptools.item(attrs):
                    if loop.begins:
                        continue
                    if not loop.final:
                        field[key] = getattr(field[key], attr)
                    temporary[key] = getattr(temporary[key], attr)
            except KeyError as e:
                raise ValueError(f'Not sopported attribute: {".".join(attrs)}: ', e)

            if len(attrs) == 1:
                if isinstance(__globals, type):
                    setattr(__globals, attrs[-1], __redefenitions[key])
                else:
                    data[attrs[-1]] = __redefenitions[key]
            else:
                setattr(field[key], attrs[-1], __redefenitions[key])

        result = wrapped(*args, **kwargs)

        for key in __redefenitions:
            attrs = key.split('__')
            if len(attrs) == 1:
                if isinstance(__globals, type):
                    setattr(__globals, attrs[-1], temporary[key])
                else:
                    data[attrs[-1]] = temporary[key]
            else:
                setattr(field[key], attrs[-1], temporary[key])
        return result

    return wrapper


temporally = _TemporaryContext

# class SquareDecorator:
#     def __init__(self, function):
#         self.function = function

#     def __call__(self, *args, **kwargs):

#         # before function
#         result = self.function(*args, **kwargs)

#         # after function
#         return result


# adding class decorator to the function
# @SquareDecorator
# def get_square(n):
#     print("given number is:", n)
#     return n * n


# get_square
# print("Square of number is:", get_square(195))


# a = temporary_globals()
# b = 12
