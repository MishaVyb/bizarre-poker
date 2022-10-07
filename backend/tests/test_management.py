from io import StringIO
import os
from pprint import pprint
import sys
from django.core.management import call_command
import pytest

@pytest.mark.django_db
class TestComands:
    def test_apply_data(self, monkeypatch):
        pprint(sys.path)
        cwd = os.getcwd()  # Get the current working directory (cwd)
        pprint(cwd)
        out = StringIO()
        monkeypatch.setattr('sys.stdin', StringIO('Y'))

        call_command(
            'apply_data',
            'apps/core/management/test_data.json',
            stdout=out,
        )
        assert 'Success' in out.getvalue()
