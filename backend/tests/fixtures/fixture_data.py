
from io import StringIO
import logging
import os
from pprint import pprint
import sys
from django.core.management import call_command
import pytest

from core.functools.utils import change_loggers_level


@pytest.fixture
def apply_default_data(monkeypatch):
        change_loggers_level(logging.ERROR)
        monkeypatch.setattr('sys.stdin', StringIO('Y'))
        call_command('apply_data')
        change_loggers_level(logging.INFO)
