import logging
from io import StringIO

import pytest
from core.utils.functools import change_loggers_level
from django.core.management import call_command

from tests.base import APIGameProperties


@pytest.mark.django_db
class TestComands:
    def test_apply_data(self, monkeypatch):
        out = StringIO()
        monkeypatch.setattr('sys.stdin', StringIO('Y'))
        call_command('apply_data', stdout=out)
        assert 'Success' in out.getvalue()

@pytest.mark.django_db
class TestForceContinueAction(APIGameProperties):
    def test_force_continue_with_default_data(
        self, apply_default_data, apply_game, setup_urls, setup_clients
    ):
        change_loggers_level(logging.ERROR)
        for _ in range(100):
            self.assert_response('', 'simusik', 'POST', 'forceContinue')
