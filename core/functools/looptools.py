"""
Import `looptools` for accessing to a defferent loop generators.

developing:
[X] clean code style
[X] pytest
[X] doc string
[X] doc string tests
[X] type hints for default value
[X] code formating / black / flake8 / isort
[X] extend API: create previous/following iter only if nesaccery
[ ] Unsupported target for indexed assignment ("Sequence[_T]")
[ ] Pytest: check behavior if source iterable is changed while looping
"""

from __future__ import annotations

from itertools import tee
from typing import (
    Generator,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Reversible,
    Sequence,
    TypeVar,
)

_T = TypeVar('_T')


class _LoopTools(Generic[_T]):
    @staticmethod
    def generator(
        __iterable: Iterable[_T], *, default: _T | None = None
    ) -> Generator[_LoopTools[_T], None, None]:
        previous_iter, current_iter, following_iter = tee(__iterable, 3)
        tools: _LoopTools[_T]

        def set_final_loop_iteration():
            tools.final = True
            if default is not None:
                tools.following = default
            else:
                delattr(tools, 'following')

        # setup
        try:
            tools = _LoopTools(
                previous=default,
                item=next(current_iter),
                following=next(following_iter),
                source=__iterable,
            )
        except StopIteration:  # iterable is epty
            return
        try:
            tools.following = next(following_iter)
        except StopIteration:
            set_final_loop_iteration()

        while True:  # main loop
            yield tools

            # iterate tools
            tools.index += 1
            tools.begins = False
            tools.previous = next(previous_iter)
            try:
                tools.item = next(current_iter)
            except StopIteration:  # reached the end of iterable
                return
            try:
                tools.following = next(following_iter)
            except StopIteration:
                set_final_loop_iteration()

    def __init__(
        self,
        item: _T,
        source: Iterable[_T],
        previous: _T | None = None,
        following: _T | None = None,
    ) -> None:
        self.item: _T = item
        self.first: _T = item
        if isinstance(source, Sequence):
            self.source: Sequence[_T] = source
        if isinstance(source, Reversible):
            self.last = next(reversed(source))

        if previous is not None:
            self.previous: _T = previous
        if following is not None:
            self.following: _T = following

        self.index: int = 0
        self.begins: bool = True
        self.final: bool = False

    @property
    def single(self) -> bool:
        """True if there are only one loop iteration."""
        return self.begins and self.final

    @property
    def has_previous(self) -> bool:
        """Checks if there is the previous element."""
        return hasattr(self, 'previous')

    @property
    def has_following(self) -> bool:
        """Checks if there is the following element."""
        return hasattr(self, 'following')

    @property
    def has_last(self) -> bool:
        """Checks if the last element is accessible.
        `last` attribute is supported only by reversible iterables."""
        return hasattr(self, 'last')

    @property
    def current(self):
        """The same as item but getting access to sourse iterable."""
        return self.source[self.index]

    @current.setter
    def current(self, value: _T):
        self.source[self.index] = value  # type: ignore


class _LoopToolsGenerators:
    @staticmethod
    def final(
        __iterable: Iterable[_T],
    ) -> Generator[tuple[_T, Literal[True]] | tuple[_T, Literal[False]], None, None]:
        """Pass through all values from the given iterable.
        Yield `item` and `True` for the last iteration.

        >>> for item, final in looptools.final('abc'):
        ...     f'{item} | {final}'
        'a | False'
        'b | False'
        'c | True'

        [ex lastloop]
        """
        it: Iterator[_T] = iter(__iterable)
        try:
            item = next(it)
        except StopIteration:  # iterable is epty
            return
        for val in it:
            yield item, False
            item = val
        yield item, True  # reached the end of iterable

    @staticmethod
    def begins(
        __iterable: Iterable[_T],
    ) -> Generator[tuple[_T, Literal[True]] | tuple[_T, Literal[False]], None, None]:
        """Pass through all values from the given iterable.
        Yield `item` and `True` for the first iteration.

        >>> for item, begins in looptools.begins('abc'):
        ...     f'{item} | {begins}'
        'a | True'
        'b | False'
        'c | False'

        [ex lastloop]
        """
        it: Iterator[_T] = iter(__iterable)
        try:
            yield next(it), True
        except StopIteration:  # iterable is epty
            return
        while True:
            try:
                yield next(it), False
            except StopIteration:
                return  # reach the end

    @staticmethod
    def item(
        __iterable: Iterable[_T], *, default: _T | None = None
    ) -> Generator[tuple[_T, _LoopTools[_T]], None, None]:
        for loop in _LoopTools.generator(__iterable, default=default):
            yield loop.item, loop

    def __call__(
        self, __iterable: Iterable[_T], *, default: _T | None = None
    ) -> Generator[_LoopTools[_T], None, None]:
        """
        Easy tools for handy looping sequences. Enjoy.

        >>> for loop in looptools('abcd', default='*'):
        ...    f'{loop.item}: [{loop.index}] | {loop.previous} {loop.following}'
        'a: [0] | * b'
        'b: [1] | a c'
        'c: [2] | b d'
        'd: [3] | c *'

        Use this syntaxis for accessing previous or following whithout default.
        >>> for loop in looptools('a'):
        ...    loop.previous if loop.has_previous else None
        ...    loop.following if loop.has_following else None

        Or catch an exeption.
        >>> next(looptools('abcd')).previous
        Traceback (most recent call last):
        ...
        AttributeError: '_LoopTools' object has no attribute 'previous'


        """
        return _LoopTools.generator(__iterable, default=default)


looptools = _LoopToolsGenerators()  # alias
"""
looptools(..)
    yield only `tools`
looptools.item(..)
    yield `tools.item` and `tools`
looptools.begins(..)
    yield `tools.item` and `tools.begins`
looptools.final(..)
    yield `tools.item` and `tools.final`
"""


if __name__ == '__main__':
    for item, loop in looptools.item('abcd', default='*'):
        print(f'{item}: [{loop.index}] | {loop.previous} {loop.item} {loop.following}')

    print('----')

    for item, loop in looptools.item('a', default='*'):
        print(f'{item}: [{loop.index}] | {loop.previous} {loop.item} {loop.following}')

    print('----')
    for loop in looptools('a'):
        loop.has_following

    for item, loop in looptools.item('abcd'):
        if loop.begins:
            print(f'begins via {loop.first}')
        nothing = '*'
        print(
            f'{item}: [{loop.index}] | '
            f'{loop.previous if loop.has_previous else nothing} {loop.item} '
            f'{loop.following if loop.has_following else nothing}'
        )
        if loop.final:
            print(f'final via {loop.last}')
