from __future__ import annotations

import logging

import pytest
from _pytest.fixtures import SubRequest as PytestSubRequest
from core.functools.decorators import temporally
from core.functools.utils import init_logger
from games.backends.cards import CardList, Decks
from games.models import Game
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User

from ..test_views import TestGame

logger = init_logger(__name__, logging.DEBUG)

import pytest


@pytest.fixture(
    params=[
        pytest.param(
            dict(
                users_amount=3,
                table=CardList('Ace|H', 'Ace|D', 'King|C', '5-c', '7-s'),
                hands=(
                    CardList('10-s', '9-s'),
                    CardList('Ace|H', '2-h'),
                    CardList('2-c', '5-h'),
                ),
                expected_combos=(
                    (
                        'one pair',
                        {'rank': [CardList('Ace|H', 'Ace|D')]},
                    ),
                    (
                        'three of kind',
                        {'rank': [CardList('Ace|H', 'Ace|H', 'Ace|D')]},
                    ),
                    (
                        'one pair',
                        {'rank': [CardList('5-c', '5-c')]},
                    ),
                ),
            ),
            id='simple test (3 players): the second one has winning combination',
        ),
    ],
)
def table_and_hands_and_expected_combos(request: PytestSubRequest):
    return request.param


@pytest.fixture
def collect_deck_from_table_and_hands(table_and_hands_and_expected_combos: dict):
    """Get custom deck from input data and set it as game deck."""
    data = table_and_hands_and_expected_combos
    table = data['table']
    hands = data['hands']

    # collect deck
    deck = CardList()
    deck.extend(table)
    for cards in zip(*reversed(hands), strict=True):
        deck.extend(cards)

    # set our test deck to the game
    setattr(Decks, 'TEST_DECK', deck)
    with temporally(Game, DECK_DEFAULT='TEST_DECK', DECK_SHUFFLING=False):
        yield
    delattr(Decks, 'TEST_DECK')


@pytest.fixture(
    # пока что у меня в этом нет обходимости, тк только один тест в классе
    # scope='class'
)
def setup_test_game_by_api(
    request: pytest.FixtureRequest,
    collect_deck_from_table_and_hands,
    table_and_hands_and_expected_combos,
):
    if request.instance is None:
        raise RuntimeError(
            'This fixture can be used only at test defined as class methods. '
        )

    self: TestGame = request.instance
    logger.info(f'test setup for {self} is processing..')

    # users
    for username in self.usernames:
        user: User = User.objects.create(username=username)
        user.set_password(user.username)
        user.save()

    # clients
    self.clients = {}
    for username, user in self.users.items():
        client = APIClient()
        client.login(username=user.username, password=user.username)
        self.clients[username] = client

        # chek user auth
        self.assert_response(
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
    self.assert_response(
        'create game', 'vybornyy', 'POST', 'games', r'', status.HTTP_201_CREATED
    )
    # remember game pk to operate test data
    self.game_pk = self.response_data['id'] # type: ignore

    # setup expected
    expected_combos = table_and_hands_and_expected_combos['expected_combos']
    self.expected_combo_names = {}
    self.expected_combo_stacks = {}
    for key, (combo_name, combo_stacks) in zip(self.users, expected_combos):
        self.expected_combo_names[key] = combo_name
        self.expected_combo_stacks[key] = combo_stacks

    # format urls
    for key, url in self.urls.items():
        if '{game_pk}' in url:
            self.urls[key] = url.format(game_pk=self.game_pk)

    # check game data no errors
    self.game.full_clean()
