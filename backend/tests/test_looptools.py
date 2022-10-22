import pytest
from core.utils import looptools


@pytest.mark.parametrize('iterable, default, expected', [
    pytest.param(
        'abcd', '*', (
            'a: [0] | * b |'
            'b: [1] | a c |'
            'c: [2] | b d |'
            'd: [3] | c * |'
        ),
        id='01 simple test'
    ),
    pytest.param(
        '', None, '',
        id='02 empty iterable not raising any errors'
    ),
])
def test_looptools(iterable: str, default: str | None, expected: str):
    result = ''
    for loop in looptools(iterable, default=default):
        result += f'{loop.item}: [{loop.index}] | {loop.previous} {loop.following} |'

    assert result == expected


@pytest.mark.parametrize('iterable, attr, expected', [

    pytest.param(
        'abcd',
        'previous',
        AttributeError("'_LoopTools' object has no attribute 'previous'"),
        id='03 previous is not avalible'
    ),
    pytest.param(
        'abcd',
        'following',
        AttributeError("'_LoopTools' object has no attribute 'following'"),
        id='04 following is not avalible'
    ),
    pytest.param(
        None, None, TypeError("'NoneType' object is not iterable"),
        id='05 None iterable raise TypeError'
    ),

])
def test_looptools_none_default_raise_exeption(
        iterable: str,
        attr: str,
        expected: Exception
):
    try:
        for loop in looptools(iterable):
            getattr(loop, attr)
    except Exception as e:
        assert e.args == expected.args
