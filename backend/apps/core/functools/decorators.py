import functools
from operator import getitem, setitem
import time
from typing import Any

from core.functools.looptools import looptools
from core.functools.utils import StrColors, init_logger, get_func_name

logger = init_logger(__name__)


class TemporaryContext:
    """Redefine variables by given kwargs and returns values back after execution.
    Could be used as decorator or context manager.

    source: dafault
        class or dict wich contains variables should be redefine
    **redefenitions:
        keyword arguments, where key is `variable name`, value is `tmp value`
        use __ (double underscore) for getting access to class attributes

    >>> Foo = type('Foo', (object,), {'bar': 1234})
    >>> with TemporaryContext(globals(), Foo__bar = 'tmp value'):
    ...     Foo.bar
    'tmp value'
    >>> Foo.bar
    1234
    """

    error_messages = (
        'Invalid `{attr}`. Are you shure source {source} has such attr? '
        'If definition of global at another module than decorator or manager is '
        'calling, you should import it before or pass class (not globals) as initial '
        'arument directly. ',
        'Invalid `{attr}` for {source}. Check class attrubutes and redefenitions keys.',
    )

    def __init__(self, source: dict[str, Any] | type, **redefenitions):
        self.source = source
        self.redefenitions = redefenitions
        self.fields: dict[str, Any] = {}
        """dict contains a `field` we-want-to-redefine per key"""
        self.values: dict[str, Any] = {}
        """dict contains a `value` of field we-want-to-redefine per key"""

    def _get(self, dict_or_type, attr_or_item):
        method = getitem if isinstance(dict_or_type, dict) else getattr
        return method(dict_or_type, attr_or_item)

    def _set(self, dict_or_type, attr_or_item, value):
        method = setitem if isinstance(dict_or_type, dict) else setattr
        method(dict_or_type, attr_or_item, value)

    def __enter__(self):
        for key in self.redefenitions:
            attrs = key.split('__')
            for attr, loop in looptools.item(attrs):
                # first iteration:
                try:
                    if loop.single:
                        self.values[key] = self._get(self.source, *attrs)
                        self._set(self.source, *attrs, self.redefenitions[key])
                        continue
                    elif loop.begins:
                        self.fields[key] = self._get(self.source, attr)
                        continue
                except KeyError or AttributeError as e:
                    message = self.error_messages[0].format(
                        attr=attr, source=self.source.__class__
                    )
                    raise ValueError(message, e)

                # second and further iterations:
                try:
                    if loop.final:
                        self.values[key] = self._get(self.fields[key], attr)
                        self._set(self.fields[key], attr, self.redefenitions[key])
                    else:
                        self.fields[key] = self._get(self.fields[key], attr)
                except (KeyError, AttributeError) as e:
                    message = self.error_messages[1].format(
                        attr=attr, source=self.fields[key]
                    )
                    raise ValueError(message, e)
        return self

    def __exit__(self, *args):
        for key in self.redefenitions:
            attrs = key.split('__')
            attr = attrs[-1]
            if len(attrs) == 1:
                self._set(self.source, attr, self.values[key])
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


temporally = TemporaryContext


@functools.total_ordering
class ProcessingTimer:
    def __init__(self, __logger=logger, name='') -> None:
        self.__logger = __logger
        self.process_period: float | None = None
        self.name = name or get_func_name(back=True)

    def __enter__(self):
        self.__logger.info(f'Start processing timer for {self.name}. ')
        self.__in = time.time()
        return self

    def __exit__(self, *args):
        self.process_period = time.time() - self.__in
        rounded = round(self.process_period, 3)
        self.__logger.info(
            f'Processing period for {self.name}: {StrColors.bold(rounded)}'
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProcessingTimer):
            return NotImplemented
        return self.process_period == other.process_period

    def __lt__(self, other: object) -> bool:
        if (
            not isinstance(other, ProcessingTimer)
            or self.process_period is None
            or other.process_period is None
        ):
            return NotImplemented
        return self.process_period < other.process_period

    def __call__(self, wrapped):
        self.name = self.name or wrapped.__name__

        @functools.wraps(wrapped=wrapped)
        def wrapper(*args, **kwargs):
            self.__enter__()
            result = wrapped(*args, **kwargs)
            self.__exit__()
            return result

        return wrapper


processing_timer = ProcessingTimer
