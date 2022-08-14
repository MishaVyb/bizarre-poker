from __future__ import annotations
import logging
import re
from typing import Any, Callable, Iterable, Literal

import pytest
from django.contrib.auth import get_user_model
from games.backends.cards import CardList, Decks, Stacks
from games.models import Game, Player
from users.models import User
from django.test import Client
from django.urls import reverse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.test import APIClient
from core.functools.utils import init_logger
import pytest
from _pytest.fixtures import SubRequest as PytestSubRequest
import requests
from pprint import pformat, pprint
from core.functools.decorators import temporally

logger = init_logger(__name__, logging.DEBUG)

# @pytest.mark.django_db
# @pytest.fixture(scope='class')
# def vybornyy():
#     user: User = User.objects.create(username='vybornyy')
#     user.set_password(user.username)
#     user.save()
#     return User.objects.get(username=user.username)

# @pytest.mark.django_db
# @pytest.fixture(scope='class')
# def simusik():
#     user: User = User.objects.create(username='simusik')
#     user.set_password(user.username)
#     user.save()
#     return User.objects.get(username=user.username)

# @pytest.mark.django_db
# @pytest.fixture(scope='class')
# def barticheg():
#     user: User = User.objects.create(username='barticheg')
#     user.set_password(user.username)
#     user.save()
#     return User.objects.get(username=user.username)


@pytest.mark.django_db
class TestGame:
    usernames = ('vybornyy', 'simusik', 'barticheg')  # host username is 'vybornyy'
    game_pk: int | None = None
    urls = {
        'games': '/api/v1/games/',
        'detail': '/api/v1/games/{pk}/',
        'join': '/api/v1/games/{pk}/join/',
        'start': '/api/v1/games/{pk}/start/',
    }

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self.game_pk)

    @property
    def players(self) -> dict[str, Player]:
        return {p.user.username: p for p in self.game.players}

    #@pytest.mark.django_db
    @pytest.fixture(
        #autouse=True,
        #scope='class',
        params=
        [
            pytest.param(
                (
                    CardList('Ace|H', 'Ace|D', 'King|C', '5-c', '7-s'),  # table
                    (
                        CardList('10-s', '9-s'),  # hand 1
                        CardList('Ace|H', '2-h'),  # hand 2
                        CardList('2-c', '5-h'),  # hand 3
                    ),
                    (
                        # expected combo 1
                        ('one pair', {'rank': [CardList('Ace|H', 'Ace|D')]}),
                        # expected combo 2
                        (
                            'three of kind',
                            {'rank': [CardList('Ace|H', 'Ace|H', 'Ace|D')]},
                        ),
                        # expected combo 3
                        ('one pair', {'rank': [CardList('5-c', '5-c')]}),
                    ),
                ),
                id='simple test',
            ),
        ],
    )
    def setup_clients_game_and_expected(
        self,
        #vybornyy: User, barticheg: User, simusik: User,
        request: PytestSubRequest
        #data: tuple
    ):
        # users
        for username in self.usernames:
            user: User = User.objects.create(username=username)
            user.set_password(user.username)
            user.save()

        # clients
        self.clients: dict[str, Client] = {}
        for username, user in self.users.items():
            client = APIClient()
            client.login(username=user.username, password=user.username)
            self.clients[username] = client

            # chek user auth
            self.assert_game_response(
                'chek user auth',
                username,
                'GET',
                'games',
                '',
                assertion_messages=(
                    (
                        'Authetication failed. '
                        'Check auth backends: SessionAuthetication should be aplyed. '
                    ),
                    None,
                ),
            )

        # create game by api
        game_detail, user_detail = self.assert_game_response(
            'create game', 'vybornyy', 'POST', 'games', r'', status.HTTP_201_CREATED
        )
        self.game_pk = game_detail['id']  # remember game pk to operate test data

        # get custom deck from input data:
        table = request.param[0]
        hands = request.param[1]
        test_deck = CardList()
        test_deck.extend(table)
        for cards in zip(*reversed(hands), strict=True):
            test_deck.extend(cards)

        # set our test deck to the game
        Decks.TEST_DECK = test_deck.copy()
        g = self.game
        g.deck_generator = 'TEST_DECK'
        g.save()

        # expected
        expected_combos = request.param[2]
        self.expected_combo_names: dict[str, str] = {}
        self.expected_combo_stacks: dict[str, dict[str, Stacks]] = {}
        for key, (combo_name, combo_stacks) in zip(self.users, expected_combos):
            self.expected_combo_names[key] = combo_name
            self.expected_combo_stacks[key] = combo_stacks

        # format urls
        for key, url in self.urls.items():
            if '{pk}' in url:
                self.urls[key] = url.format(pk=self.game_pk)

        # check game data no errors
        self.game.full_clean()

    @temporally(Game, DECK_SHUFFLING=False)
    def test_game_by_api(
        self,
        setup_clients_game_and_expected
        ):
        # [0] test get game detail by host
        game_detail, user_detail = self.assert_game_response(
            'test get game detail by host',
            'vybornyy',
            'GET',
            'detail',
            r'HostApprovedGameStart not sytisfyed',
        )
        # user_detail = r.data['players_detail'][0]
        assert user_detail['host'] is True, 'Vybornyy should be host. '
        assert user_detail['dealer'] is True, 'Vybornyy should be dealer. '
        assert user_detail['position'] is 0, 'Vybornyy should be at first position. '

        # test: if host leave the game
        ...

        # test: if host join game again
        ...

        # test: if no player want look at game deteail
        ...

        # test: start with no other players
        ...

        # test other players join game
        self.assert_game_response(
            'test other players join game',
            ['simusik', 'barticheg'],
            'POST',
            'join',
            r'(simusik|barticheg) joined',
        )

        # [1] check game status befor start
        self.assert_game_response(
            'check game status before start',
            'vybornyy',
            'GET',
            'detail',
            r'HostApprovedGameStart not sytisfyed',
        )

        # test other player press `start`
        self.assert_game_response(
            'test other player press `start`',
            ['simusik', 'barticheg'],
            'POST',
            'start',
            r'',
            status.HTTP_403_FORBIDDEN,
        )

        # test host press `start`
        self.assert_game_response(
            'test host press `start`',
            'vybornyy',
            'POST',
            'start',
            r'started',
        )

        # test blinds
        ...

        # [2] check game status before bidding
        game, user = self.assert_game_response(
            'check game status before bidding',
            'vybornyy',
            'GET',
            'detail',
            r'should make a bet',
        )
        # assert user['hand'] == self.players['vybornyy'].hand
        # assert game

    def assert_game_response(
        self,
        test_name: str,
        by_users: str | Iterable[str],
        method: Literal['GET'] | Literal['POST'],
        url_name: str,
        status_pattern: str,
        expected_status: int = status.HTTP_200_OK,
        assertion_messages: tuple[str | None, ...] = (None, None),
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if isinstance(by_users, str):
            by_users = (by_users,)

        logger.info(f'TESTING: {test_name}')
        for user in by_users:

            # act
            call = getattr(self.clients[user], method.lower())
            response: Response = call(self.urls[url_name])
            response_str = pformat(dict(response.data), width=150, sort_dicts=False)

            # assert response status code
            assert response.status_code == expected_status, (
                assertion_messages[0]
                or f'Got unexpected response code. Response: {response_str}'
            )

            # assert status pattern match
            if status_pattern:
                assert re.findall(status_pattern, response.data['status']), (
                    assertion_messages[1]
                    or f'Got unexpected status: Status {response.data["status"]}'
                )

            logger.info(f'RESPONSE: \n {response_str}')

        # if self.game_pk is None:
        #     return response.data, {}

        # index = self.players[user].position
        return (
            response.data,
            response.data.get('pluser') if isinstance(response.data, dict) else None,
        )


############################################################################################

# class UserApiClient:


#     def __init__(self, user: User) -> None:
#         requests.post()
#         Client().head =


@pytest.mark.django_db
class TestGameApi:
    # url_auth = '/api/v1/jwt/create'
    # url_create_token = '/api/v1/jwt/create/'
    # url_get_users = '/api/v1/users/'
    url_games = '/api/v1/games/'
