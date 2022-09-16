from __future__ import annotations
from copy import copy


import logging
import re
from pprint import pformat
from typing import Any, Iterable, Literal

import pytest
from core.functools.decorators import temporally
from core.functools.utils import StrColors, init_logger
from games.services.cards import Stacks
from games.models import Game, Player
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient
from users.models import User
from core.types import JSON
from django.http import HttpResponsePermanentRedirect
from tests.base import BaseGameProperties
from games.services.combos import Combo
logger = init_logger(__name__, logging.DEBUG)


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'setup_clients',
    'setup_game_by_api',
    #'setup_expected_combos',
    'setup_urls',
)
class TestGameAPI(BaseGameProperties):
    urls = {
        'games': '/api/v1/games/',
        'game_detail': '/api/v1/games/{game_pk}/',
        'join': '/api/v1/games/{game_pk}/join/',
        'start': '/api/v1/games/{game_pk}/start/',
        'players': '/api/v1/games/{game_pk}/players/',
        'user_player': '/api/v1/games/{game_pk}/players/user/',
        'other_players': '/api/v1/games/{game_pk}/players/other/',
        'bet': '/api/v1/games/{game_pk}/bet/',
    }
    clients: dict[str, APIClient]
    expected_combos: dict[str, Combo]

    response_data: JSON

    def test_game_api(self):
        # [0] test get game detail by host
        self.assert_response(
            'test get game detail by host',
            'vybornyy',
            'GET',
            'game_detail',
            r'HostApprovedGameStart not sytisfyed',
        )
        self.make_log('vybornyy')
        vybornyy = self.response_data['players_detail'][0]
        assert vybornyy['position'] is 0, 'should be at first position. '
        assert vybornyy['is_host'] is True, 'should be host. '
        assert vybornyy['is_dealer'] is True, 'should be dealer. '

        return

        # test: if host leave the game
        ...

        # test: if host join game again
        ...

        # test: if no player want look at game deteail
        ...

        # test: start with no other players
        ...

        # test other players join game
        self.assert_response(
            'test other players join game',
            ['simusik', 'barticheg'],
            'POST',
            'join',
            r'(simusik|barticheg) joined',
        )

        # test_players_api(self):
        self.assert_response('test players api', 'vybornyy', 'GET', 'players')

        # [1] check game status befor start
        self.assert_response(
            'check game status before start',
            'vybornyy',
            'GET',
            'game_detail',
            r'HostApprovedGameStart not sytisfyed',
        )

        # test other player press `start`
        self.assert_response(
            'test other player press `start`',
            ['simusik', 'barticheg'],
            'POST',
            'start',
            r'',
            status.HTTP_403_FORBIDDEN,
        )

        # test host press `start`
        self.assert_response(
            'test host press `start`',
            'vybornyy',
            'POST',
            'start',
            r'started',
        )

        # test blinds values
        ...

        # [2] update game status before bidding
        self.assert_response(
            'update game status before bidding',
            'simusik',
            'GET',
            'game_detail',
            r'should make a bet or say "pass"',  # vybornyy
        )

        # test players hand hiden or not
        self.assert_response(
            'test players hand hiden or unhiden',
            'vybornyy',
            'GET',
            'players',
        )
        assert self.response_data[0]['hand'] == str(self.players['vybornyy'].hand)
        assert self.response_data[1]['user'] == 'simusik'  # assert ordering
        assert self.response_data[1]['hand'] == self.players['simusik'].hand.hiden()

        # test user_player endpoint
        self.assert_response(
            'test user_player return requested user`s plaer',
            'barticheg',
            'GET',
            'user_player',
        )
        assert self.response_data['user'] == 'barticheg'
        self.assert_response(
            'test other_player return list with len=2 and check playrs positions',
            'simusik',
            'GET',
            'other_players',
        )
        assert len(self.response_data) == 2
        assert self.response_data[0]['user'] == 'vybornyy'
        assert self.response_data[0]['position'] == 0
        assert self.response_data[1]['user'] == 'barticheg'
        assert self.response_data[1]['position'] == 2

        ...
        ...
        ...
        ...
        return

        # [3] biddings
        self.assert_response(
            'test player who already place a bet could not place it again',
            'simusik',
            'POST',
            'bet',
            post_data={'value': 0},
        )
        err_message = f'simusik can not place a bet because {self.game.status}'
        assert self.response_data['errors']['game_status'] == err_message

        bet_value = 12345
        self.assert_response(
            'test bet maker place more that his bank account',
            'vybornyy',
            'POST',
            'bet',
            post_data={'value': bet_value},
        )
        err_message = f'vybornyy can not place {bet_value} because it more than his bank {self.users["vybornyy"].profile.bank}'
        assert self.response_data['errors']['value'] == err_message

    def assert_response(
        self,
        test_name: str,
        by_users: str | Iterable[str],
        method: Literal['GET'] | Literal['POST'],
        url_name: str,
        status_pattern: str = '',
        expected_status: int = status.HTTP_200_OK,
        assertion_messages: tuple[str | None, ...] = (None, None),
    ):
        if isinstance(by_users, str):
            by_users = (by_users,)

        logger.info(f'{StrColors.purple("TESTING")}: {test_name}')
        for user in by_users:
            # act
            call = getattr(self.clients[user], method.lower())
            response: Response = call(self.urls[url_name])

            if isinstance(response, HttpResponsePermanentRedirect):
                logger.warning(
                    f'Recieved Permanent Redirect Response: '
                    f'frorm {self.urls[url_name]} to {response.url}. '
                    f'Hint: check requested url, it shoul be ended with / (slash)'
                )

            # assert response status code
            assert response.status_code == expected_status, (
                assertion_messages[0]
                or f'Got unexpected response code. Response data: {response.data}'
            )
            # assert status pattern match
            if status_pattern and response.data.get('status'):
                assert re.findall(status_pattern, response.data['status']), (
                    assertion_messages[1]
                    or f'Got unexpected status: Status {response.data["status"]}'
                )
        self.response_data = response.data

    def make_log(self, user: str, width=150):
        """Formating response data in certain way and log it."""
        try:
            data = copy(self.response_data)
            data_str = pformat(data, width=width, sort_dicts=False)
            data_str = re.sub(user, StrColors.green(user), data_str)
        except Exception as e:
            logger.error(f'Formating log fialed: {e}')
            pass

        logger.info(f'RESPONSE: \n {data_str}')
