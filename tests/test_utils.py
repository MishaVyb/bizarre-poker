import pytest

from core.functools.utils import eq_first


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
