from __future__ import annotations

import logging
from pprint import pformat

import pytest
from django.test.utils import CaptureQueriesContext
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db import connection
from core.functools.utils import init_logger, StrColors

logger = init_logger(__name__)


def param_kwargs(_id: str = None, _marks=(), **kwargs: object):
    """Usage:

    >>> pytets.fuxture(params=[
    ...        param_kwargs(...),
    ...        param_kwargs(...),
    ...        ...
    ...    ])
    """
    return pytest.param(dict(**kwargs), marks=_marks, id=_id)


def param_kwargs_list(_id: str = None, _marks=(), **kwargs: object):
    """Usage:

    >>> pytets.mark.parametrize('attr_one, attr_two, attr_other, ..', [
    ...        param_kwargs_list(..),
    ...        param_kwargs_list(..),
    ...        ...
    ...    ])
    """
    return pytest.param(*kwargs.values(), marks=_marks, id=_id)


class ExtendedQueriesContext(CaptureQueriesContext):
    def __init__(
        self,
        connection: BaseDatabaseWrapper = connection,
        logger: logging.Logger | None = logger,
        sql_report: bool = False,
    ) -> None:
        self._logger = logger
        self._sql_report = sql_report
        super().__init__(connection)

    def __enter__(self) -> ExtendedQueriesContext:
        if self._logger:
            self._logger.info(StrColors.purple('Start capturing quries. '))
        return super().__enter__()

    def __exit__(self, exc_type: None, exc_value: None, traceback: None) -> None:
        if self._logger:
            if self._sql_report:
                self.log_and_clear('final')
            self._logger.info(
                f'{StrColors.purple("End capturing quries")}. '
                f'Total amount: {StrColors.bold(self.total_amount)}. '
                f'Total dublicated: {StrColors.bold(self.total_dublicated)}. '
            )

        return super().__exit__(exc_type, exc_value, traceback)

    _total_amount = 0

    @property
    def total_amount(self):
        return self._total_amount + self.amount

    _total_original = 0

    @property
    def total_original(self):
        return self._total_original + self.amount_original

    @property
    def total_dublicated(self):
        return self.total_amount - self.total_original

    @property
    def amount(self):
        return len(self.captured_queries)

    @property
    def amount_original(self):
        original_set = set(map(lambda q: q['sql'], self.captured_queries))
        return len(original_set)

    @property
    def amount_dublicated(self):
        return self.amount - self.amount_original

    @property
    def formated_quries(self):
        all_querise = self.captured_queries
        all_quries_str = (
            pformat(all_querise)
            .replace('"', '')
            .replace("'", '')
            .replace('SELECT', StrColors.cyan('SELECT'))
            .replace('UPDATE', StrColors.red('UPDATE'))
            .replace('games_', '')
            .replace('auth_', '')
        )
        return all_quries_str

    def log_and_clear(self, log_name: str = ''):
        assert self._logger, 'logger should be torn on'

        detail = ''
        if self.captured_queries and self._sql_report:
            detail = f'Captured SQL queries: \n{self.formated_quries}\n'

        self._logger.info(
            f'{StrColors.cyan(log_name)}. '
            f'Current amount: {StrColors.bold(self.amount)}. '
            f'Current dublicated: {StrColors.bold(self.amount_dublicated)}. '
            f'{detail}'
        )

        self._total_amount += self.amount
        self._total_original += self.amount_original
        self.initial_queries = len(self.connection.queries_log)
