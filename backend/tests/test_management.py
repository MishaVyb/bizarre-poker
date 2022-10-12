from io import StringIO
import os
from pprint import pprint
import sys
from django.core.management import call_command
import pytest


@pytest.mark.django_db
class TestComands:
    def test_apply_data(self, monkeypatch):
        out = StringIO()
        monkeypatch.setattr('sys.stdin', StringIO('Y'))
        call_command('apply_data', stdout=out)
        assert 'Success' in out.getvalue()
