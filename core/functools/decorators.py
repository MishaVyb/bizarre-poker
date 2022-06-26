"""

developing:
[ ] doc test -- not working
[ ] exclude additional imports
[X] pytest
"""


from functools import wraps
from typing import Any
from core.functools.looptools import looptools
from games.backends.cards import Card, JokerCard

import wrapt


def temporary_globals(**__redefenitions):
    """Temporary redefenitions for global variables.
    Globals have to be imported to decorators module.
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
    @wrapt.decorator    # also work as functools.wraps
    def wrapper(wrapped, instance, args, kwargs):
        glb = globals()
        lcls = locals()

        field: dict[str, Any] = {}
        temporary: dict[str, Any] = {}
        for key in __redefenitions:
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
                globals()[attrs[-1]] = __redefenitions[key]
            else:
                setattr(field[key], attrs[-1], __redefenitions[key])

        result = wrapped(*args, **kwargs)

        for key in __redefenitions:
            attrs = key.split('__')
            if len(attrs) == 1:
                globals()[attrs[-1]] = temporary[key]
            else:
                setattr(field[key], attrs[-1], temporary[key])
        return result
    return wrapper


# tests:
class Foo:
    fff = 1234
    class Bar:
        aaa = 1234
        bbb = 'qwerty'

def test_temporary_globals__():
    new_tmp_values = {
        'Foo': type('NewClass', (object,), {'qqq': -1, 'fff': 1234, 'Bar': Foo.Bar}),
        'Foo__fff': -1,
        'Foo__Bar__aaa': -1,
    }

    @temporary_globals(**new_tmp_values)
    def func():
        assert Foo == new_tmp_values['Foo']
        assert hasattr(Foo, 'qqq')
        assert Foo.qqq == -1
        assert Foo.fff == new_tmp_values['Foo__fff']
        assert Foo.Bar.aaa == new_tmp_values['Foo__Bar__aaa']
        assert Foo.Bar.bbb == 'qwerty'

    func()
    assert not hasattr(Foo, 'qqq')
    assert hasattr(Foo, 'fff')
    assert Foo.fff == 1234
    assert Foo.Bar.aaa == 1234
    assert Foo.Bar.bbb == 'qwerty'