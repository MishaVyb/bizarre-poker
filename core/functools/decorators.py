"""

developing:
[ ] doc
[ ] exclude additional imports
[ ] pytest
"""


from functools import wraps
from typing import Any
from core.functools.looptools import looptools
from games.backends.cards import Card, JokerCard

import wrapt


def temporary_globals(module: str = '', **redefenitions):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        glpb = globals()
        print('in')
        print(*glpb, sep='\n')

        field: dict[str, Any] = {}
        temporary: dict[str, Any] = {}
        for key in redefenitions:
            attrs = key.split('__')
            try:
                temporary[key] = globals()[attrs[0]]
                field[key] = globals()[attrs[0]]
                for attr, loop in looptools.item(attrs):
                    if loop.begins:
                        continue
                    if not loop.final:
                        field[key] = getattr(field[key], attr)
                    temporary[key] = getattr(temporary[key], attr)
            except Exception as e:
                raise ValueError(f"not sopported attribute: {'.'.join(attrs)}", *e.args)

            if len(attrs) == 1:
                globals()[attrs[-1]] = redefenitions[key]
            else:
                setattr(field[key], attrs[-1], redefenitions[key])

        result = wrapped(*args, **kwargs)

        for key in redefenitions:
            attrs = key.split('__')
            if len(attrs) == 1:
                globals()[attrs[-1]] = temporary[key]
            else:
                setattr(field[key], attrs[-1], temporary[key])
        print('out')
        return result

    return wrapper


class Foo:
    fff = 10000

    class Bar:
        aaa = 1234
        bbb = 'qwerty'


SPEC = 'eeeeee'


def with_keyword_only_arguments(**mykwargs):
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        print('in')
        res = wrapped(*args, **kwargs)
        print('out')
        return res

    return wrapper


@with_keyword_only_arguments(aaa=123)
def test_1():
    print('do fun')


@temporary_globals(Foo__Bar__aaa=-1, Foo__fff=-1, SPEC={'keeey': -4321})
def test_2():
    '''dooooo some'''
    print('do fun 2 ---> ', end='')
    print(Foo.Bar.aaa, Foo.Bar.bbb, Foo.fff, SPEC, sep=' ')


if __name__ == '__main__':
    print(Foo.Bar.aaa, Foo.Bar.bbb, Foo.fff, SPEC, sep=' ')
    test_2()
    print(Foo.Bar.aaa, Foo.Bar.bbb, Foo.fff, SPEC, sep=' ')
    print(Foo.Bar.aaa, Foo.Bar.bbb, Foo.fff, SPEC, sep=' ')
