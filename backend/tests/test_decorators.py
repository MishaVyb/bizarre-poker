from core.functools.decorators import temporally


# for test porpuses
TEST_GLOBAL = 'default'


class Foo:
    fff = 1234

    class Bar:
        aaa = 1234
        bbb = 'qwerty'


def test_temporally_as_decorator():
    new_tmp_values = {
        'Foo': type('NewClass', (object,), {'qqq': -1, 'fff': 1234, 'Bar': Foo.Bar}),
        'Foo__fff': -1,
        'Foo__Bar__aaa': -1,
    }

    @temporally(globals(), **new_tmp_values)
    def func(some_attr: int, other: str):
        assert some_attr == 'some value'
        assert Foo == new_tmp_values['Foo']
        assert hasattr(Foo, 'qqq')
        assert Foo.qqq == -1    # type: ignore
        assert Foo.fff == new_tmp_values['Foo__fff']
        assert Foo.Bar.aaa == new_tmp_values['Foo__Bar__aaa']
        assert Foo.Bar.bbb == 'qwerty'
        return 1234

    func('some value', 'other value')
    assert not hasattr(Foo, 'qqq')
    assert hasattr(Foo, 'fff')
    assert Foo.fff == 1234
    assert Foo.Bar.aaa == 1234
    assert Foo.Bar.bbb == 'qwerty'


def test_temporally_as_context_manager():
    new_tmp_values = {
        'Foo': type('NewClass', (object,), {'qqq': -1, 'fff': 1234, 'Bar': Foo.Bar}),
        'TEST_GLOBAL': 'here is a new value',
        'Foo__fff': -1,
        'Foo__Bar__aaa': -1,
    }

    with temporally(globals(), **new_tmp_values):
        assert Foo == new_tmp_values['Foo']
        assert hasattr(Foo, 'qqq')
        assert Foo.qqq == -1
        assert TEST_GLOBAL == new_tmp_values['TEST_GLOBAL']
        assert Foo.fff == new_tmp_values['Foo__fff']
        assert Foo.Bar.aaa == new_tmp_values['Foo__Bar__aaa']
        assert Foo.Bar.bbb == 'qwerty'

    assert not hasattr(Foo, 'qqq')
    assert hasattr(Foo, 'fff')
    assert TEST_GLOBAL == 'default'
    assert Foo.fff == 1234
    assert Foo.Bar.aaa == 1234
    assert Foo.Bar.bbb == 'qwerty'
