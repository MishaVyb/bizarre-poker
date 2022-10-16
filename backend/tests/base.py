from __future__ import annotations
from itertools import chain
import itertools

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


logger = init_logger(__name__)


@pytest.mark.usefixtures('setup_users')
class BaseGameProperties:
    usernames = ('vybornyy', 'simusik', 'barticheg')
    'List of usernames who will be in the game. '
    staff_users = (
        'vybornyy',
        'simusik',
    )
    'Defined at setup_users'
    game_pk: int
    'Current game id'
    initial_users_bank: dict[str, int]
    'Defined at setup_users_bank fixture. '

    @property
    def users(self) -> dict[str, User]:
        """Users in the game. `Fresh` data from db."""
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def users_list(self) -> list[User]:
        """Users in the game. `Fresh` data from db."""
        return [User.objects.get(username=name) for name in self.usernames]

    # we use not cahced property to force test assertion compare real db value with
    # expected result (the same for other)
    @property
    def game(self) -> Game:
        """
        Game with prefetched players at manager and with players selector.
        `Fresh` data from db.

        Note:
        it makes new query evry time(!) so it will be another game instanse every time.
        """
        return Game.objects.prefetch_players().get(pk=self.game_pk).select_players(force_cashing=True)

    @property
    def players(self) -> dict[str, Player]:
        """Players in the game. `Fresh` data from db."""
        return {user.username: user.players.get(game=self.game) for user in self.users_list}

    @property
    def players_list(self) -> list[Player]:
        """Players in the game. `Fresh` data from db."""
        return [user.players.get(game=self.game) for user in self.users_list]

    def __str__(self) -> str:
        return self.__class__.__name__


class APIGameProperties(BaseGameProperties):

    urls = {
        # fmt: off
        # create, delete, retrive, list, delete
        'games': '/api/v1/games/',
        'game_detail': '/api/v1/games/{game_pk}/',

        # create, retrive, list
        'playersPreform': '/api/v1/games/{game_pk}/playersPreform/',

        # get players, player detail
        # create: join game
        # delete: leave game
        'players': '/api/v1/games/{game_pk}/players/',
        'players/{username}': '/api/v1/games/{game_pk}/players/{username}/',
        'players/me': '/api/v1/games/{game_pk}/players/me/',
        'players/other': '/api/v1/games/{game_pk}/players/other/',

        # get: all possible game actions:
        'actions': '/api/v1/games/{game_pk}/actions/',

        # make action:
        'start': '/api/v1/games/{game_pk}/actions/start/',
        'pass': '/api/v1/games/{game_pk}/actions/pass/',
        'blind': '/api/v1/games/{game_pk}/actions/blind/',
        'bet': '/api/v1/games/{game_pk}/actions/bet/',
        'check': '/api/v1/games/{game_pk}/actions/check/',
        'reply': '/api/v1/games/{game_pk}/actions/reply/',
        'vabank': '/api/v1/games/{game_pk}/actions/vabank/',
        'forceContinue': '/api/v1/games/{game_pk}/actions/forceContinue/',
        # fmt: on
    }
    clients: dict[str, APIClient]

    @property
    def participant(self):
        """
        User at `PlayerPreform` model who is wating fot joining to game.
        """
        return User.objects.get(username='participant')

    # data after act:
    request_username: str
    response_data: JSON

    @property
    def response_joined(self) -> str:
        chain = itertools.chain(self.response_data.values())
        listed: list = list(*chain)
        return ' '.join(listed)

    def assert_response(
        self,
        test_name: str,
        by_user: str | User,
        method: Literal['GET'] | Literal['POST'],
        url_name: str,
        expected_status: int | None = status.HTTP_200_OK,
        assertion_message: str = '',
        **post_data,
    ):
        # logging:
        expected = '??'
        if expected_status:
            if status.is_success(expected_status):
                expected = StrColors.green(expected_status)
            elif status.is_client_error(expected_status):
                expected = StrColors.red(expected_status)
            else:
                expected = StrColors.bold(expected_status)
        request_detail = f'{by_user} -> {method} -> {self.urls[url_name]} -> {expected} expected'
        logger.info(f'{StrColors.purple("TESTING")}: {test_name} | {request_detail}')

        # act
        name = by_user if isinstance(by_user, str) else by_user.username
        call = getattr(self.clients[name], method.lower())
        response: Response = call(self.urls[url_name], post_data)

        if status.is_redirect(response.status_code):
            logger.warning(
                f'Status code is redirect: from {self.urls[url_name]} to {response.url}. '
                f'Hint: check requested url, it shoul be ended with / (slash)'
            )

        # assert response status code
        if expected_status:
            assertion_message = assertion_message or pformat(
                f'Get unexpected response code: {response.status_code} {response}. '
                f'Response data: {getattr(response, "data", None)}. '
                f'Request detail: {request_detail}. '
            )
            assert response.status_code == expected_status, assertion_message

        self.request_username = name
        self.response_data = response.json() if response.data else {}

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
