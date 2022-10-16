from __future__ import annotations

from typing import Type, TypeVar

import pytest
from tests.base import APIGameProperties
from core.functools.decorators import temporally
from core.functools.utils import StrColors, get_func_name, init_logger
from games.models import Game
from games.models.player import PlayerPreform
from games.services.cards import Decks

from rest_framework.test import APIClient
from tests.base import BaseGameProperties
from tests.test_api import TestGameAPI
from users.models import User

logger = init_logger(__name__)
_T = TypeVar('_T')


########################################################################################
# Arrange base test data
########################################################################################

def assert_base_class(instance: BaseGameProperties, _type: Type[_T] = BaseGameProperties) -> _T:
    message = 'This fixture is only for BaseGameProperties methods. '
    assert isinstance(instance, _type), message
    logger.info(StrColors.purple(f'{get_func_name(back=True)} for {instance}'))
    return instance


@pytest.fixture
def setup_users(request: pytest.FixtureRequest):
    # this fixture is used as enter point to all class fixutres,
    # so new line for more readable logging
    print('\n')
    self: BaseGameProperties = assert_base_class(request.instance)

    for username in self.usernames:
        user: User = User.objects.create(username=username, password=username)
        user.set_password(user.username)  # othrwise password won't be supplyed
        user.save()


@pytest.fixture
def setup_game(
    request: pytest.FixtureRequest,
):
    self: BaseGameProperties = assert_base_class(request.instance)
    self.game_pk = Game(players=self.users.values(), commit=True).pk


@pytest.fixture
def setup_deck_get_expected_combos(request: pytest.FixtureRequest, table_and_hands_and_expected_combos: dict):
    self: BaseGameProperties = assert_base_class(request.instance)
    data = table_and_hands_and_expected_combos
    deck = Decks.factory_from(table=data['table'], hands=data['hands'])

    # check test arrange
    flops = sum(self.game.config.flops_amounts)
    neccessary_amount = len(self.usernames) * self.game.config.deal_cards_amount + flops
    if deck.length != neccessary_amount:
        pytest.skip('Current test deck intended for another players amount. ' f'{deck.length} != {neccessary_amount}')

    # set our test deck to the game
    setattr(Decks, 'TEST_DECK', deck)
    with temporally(
        self.game.config,
        deck_shuffling=False,
        deck_container_name='TEST_DECK',
    ):
        yield data['expected_combos'], data['rate_groups']
    delattr(Decks, 'TEST_DECK')


@pytest.fixture
def setup_users_banks(request: pytest.FixtureRequest):
    self: BaseGameProperties = assert_base_class(request.instance)

    banks: list[int] = []
    for i, u in enumerate(self.users_list):
        u.profile.bank = (i + 1) * 1000 + (i + 1) * 10
        u.profile.save()
        banks.append(u.profile.bank)

    self.initial_users_bank = {name: bank for name, bank in zip(self.usernames, banks)}
    return banks


########################################################################################
# Arrange API test data
########################################################################################


@pytest.fixture
def setup_urls(request: pytest.FixtureRequest):
    self = assert_base_class(request.instance, APIGameProperties)

    for key, url in self.urls.items():
        try:
            self.urls[key] = url.format(game_pk=self.game_pk)
        except KeyError:
            continue

    url = self.urls['players/{username}']
    for name in self.usernames:
        self.urls[f'players/{name}'] = url.format(game_pk=self.game_pk, username=name)


@pytest.fixture
def setup_clients(request: pytest.FixtureRequest):
    self = assert_base_class(request.instance, APIGameProperties)
    self.clients = {}
    self.clients['anonymous'] = APIClient()

    for user in User.objects.all():
        client = APIClient()
        client.login(username=user.username, password=user.username)
        self.clients[user.username] = client

        # chek user auth
        self.assert_response(
            'chek user auth',
            user.username,
            'GET',
            'games',
            assertion_message=('Authetication failed. Check auth backends: SessionAuthetication should be aplyed. '),
        )


@pytest.fixture
def setup_participant(
    request: pytest.FixtureRequest,
):
    self = assert_base_class(request.instance, APIGameProperties)
    self.participant = User.objects.create(username='participant', password='participant')
    PlayerPreform.objects.create(user=self.participant, game=self.game)
