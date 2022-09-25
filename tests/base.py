from __future__ import annotations

import pytest
from core.functools.utils import init_logger
from games.models import Game, Player
from users.models import User
from typing import Iterable, Literal, OrderedDict
from rest_framework import status
from rest_framework.response import Response
from copy import copy

import re
from pprint import pformat
from typing import Iterable, Literal, OrderedDict

import pytest
from core.functools.utils import StrColors, init_logger
from rest_framework import status

from rest_framework.test import APIClient
from core.types import JSON
from django.http import HttpResponsePermanentRedirect

from games.services.combos import Combo
from games.services.auto import autoplay_game

logger = init_logger(__name__)


@pytest.mark.usefixtures('setup_users')
class BaseGameProperties:
    usernames = ('vybornyy', 'simusik', 'barticheg')
    game_pk: int

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    # we use not cahced property to force test assertion compare real db value with
    # expected result (the same for other)
    @property
    def game(self) -> Game:
        """Game with prefetched players at manager and with players selector.

        Note:
        it makes new query evry time(!) so it will be another game instanse every time.
        """
        return (
            Game.objects.prefetch_players()
            .get(pk=self.game_pk)
            .select_players(force_cashing=True)
        )

    @property
    def players(self) -> dict[str, Player]:
        return {
            user.username: user.players.get(game=self.game) for user in self.users_list
        }

    @property
    def players_list(self) -> list[Player]:
        return [user.players.get(game=self.game) for user in self.users_list]

    def __str__(self) -> str:
        return self.__class__.__name__


class APIGameProperties(BaseGameProperties):
    urls = {
        'games': '/api/v1/games/',
    }
    clients: dict[str, APIClient]

    # data after act:
    request_username: str
    response_data: JSON

    def assert_response(
        self,
        test_name: str,
        by_users: str | Iterable[str],
        method: Literal['GET'] | Literal['POST'],
        url_name: str,
        data: JSON = {},
        status_pattern: str = '',
        expected_status: int = status.HTTP_200_OK,
        assertion_messages: tuple[str | None, ...] = (None, None),

    ):
        if isinstance(by_users, str):
            by_users = (by_users,)

        request_detail = f'{by_users} -> {method} -> {self.urls[url_name]}'
        logger.info(StrColors.purple(f'TESTING: {test_name} | {request_detail}'))

        for user in by_users:
            # act
            call = getattr(self.clients[user], method.lower())
            response: Response = call(self.urls[url_name], data)

            if isinstance(response, HttpResponsePermanentRedirect):
                logger.warning(
                    f'Recieved Permanent Redirect Response: '
                    f'frorm {self.urls[url_name]} to {response.url}. '
                    f'Hint: check requested url, it shoul be ended with / (slash)'
                )

            # assert response status code
            assert response.status_code == expected_status, (
                assertion_messages[0]
                or f'Get unexpected response code: {response.status_code} {response}. '
                f'Response data: {getattr(response, "data", None)}. '
                f'Request detail: {request_detail}. '
            )
        self.request_username = user
        self.response_data = response.data

    def make_log(self, user: str = '', width=150):
        """Formating response data in certain way and log it."""
        user = user or self.request_username

        data = copy(self.response_data)
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, OrderedDict):
                    data[i] = dict(item)
        else:
            for key, item in data.items():
                if isinstance(item, OrderedDict):
                    data[key] = dict(item)

        data_str = pformat(data, width=width, sort_dicts=False)
        data_str = re.sub(user, StrColors.green(user), data_str)
        
        logger.info(f'RESPONSE: \n {data_str}')
