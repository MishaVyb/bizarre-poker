from typing import Type
import pydantic
import pytest


from core.utils.functools import eq_first
from core.utils import Interval
from games.services.cards import Card
from pydantic.error_wrappers import ValidationError

@pytest.mark.parametrize(
    "minor, major, expected",
    [
        ('sima', 'Sima loves you', True),
        ('s', 'Sima loves you', True),
        ('sima', 'M', False),
        ('sima', 'misha', False),
        ('si', 's', False),
        ('s', 's', True),
        ('', 's', False),
        ('', '', True),
    ],
)
def test_eq_first(minor, major, expected: bool):
    assert eq_first(minor, major) == expected


@pytest.mark.parametrize(
    "minor, major, expected",
    [
        ('sima', 'Sima loves you', False),
        ('SimA', 'Sima loves you', False),
        ('Sima', 'Sima loves you', True),
        ('s', 'Sima loves you', False),
        ('sima', 'M', False),
        ('sima', 'misha', False),
        ('si', 's', False),
        ('s', 's', True),
        ('', 's', False),
        ('', '', True),
    ],
)
def test_eq_first_case_sensitive(minor, major, expected: bool):
    assert eq_first(minor, major, case_sensitive=True) == expected


@pytest.mark.parametrize('interval_kwargs, exception', [
    pytest.param(dict(min=10, max=10, step=10), None),
    pytest.param(dict(min=Card('2|H'), max=Card('Ace|S')), None),
    pytest.param(dict(min=5, max='3345'), ValidationError, id='different types failed'),
    pytest.param(dict(min=Card('Ace|H'), max=Card('King|H')), ValidationError),
    pytest.param(dict(min=10, max=20, step=20), ValidationError),
])
def test_interval_validation(interval_kwargs, exception: Type[Exception] | None ):
    if exception:
        with pytest.raises(exception):
            Interval(**interval_kwargs)
    else:
        Interval(**interval_kwargs)




