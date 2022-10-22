
import logging
import os
import sys
from io import StringIO
from pprint import pprint

import pytest
from core.utils import change_loggers_level
from django.core.management import call_command


@pytest.fixture
def apply_default_data(monkeypatch):
        change_loggers_level(logging.ERROR)
        monkeypatch.setattr('sys.stdin', StringIO('Y'))
        call_command('apply_data')
        change_loggers_level(logging.INFO)
