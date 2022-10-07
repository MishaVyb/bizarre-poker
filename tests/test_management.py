from io import StringIO
from django.core.management import call_command
from django.test import TestCase
import pytest

@pytest.mark.django_db
class TestComands:
    def test_apply_data(self, monkeypatch):
        out = StringIO()
        monkeypatch.setattr('sys.stdin', StringIO('Y'))
        call_command(
            'apply_data',
            'static/management/data.json',
            stdout=out,
        )
        assert 'success' in out.getvalue()
