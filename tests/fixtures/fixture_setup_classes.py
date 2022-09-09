from __future__ import annotations
from typing import TypeVar

import pytest
from core.functools.decorators import temporally
from core.functools.utils import StrColors, init_logger, logging, get_func_name
from games.backends.cards import CardList, Decks
from games.backends.combos import Combo
from games.models import Game
from games.services.configurations import DEFAULT
from rest_framework import status
from rest_framework.test import APIClient
from tests.base import BaseGameProperties
from users.models import User

logger = init_logger(__name__, logging.DEBUG)
_T = TypeVar('_T')


def assert_base_class(
    instance: BaseGameProperties, _type: type[_T] = BaseGameProperties
) -> _T:
    assert isinstance(
        instance, _type
    ), 'This fixture is only for BaseGameProperties methods. '
    logger.info(StrColors.purple(f'{get_func_name(back=True)} for {instance}'))
    return instance


# !?
# scope='class' -- пока что нет необходимости, тк только один тест в классе
@pytest.fixture
def setup_users(
    request: pytest.FixtureRequest,
):
    # this fixture is used as enter point to all class fixutres,
    # so new line for more readable logging
    print('\n')
    self: BaseGameProperties = assert_base_class(request.instance)

    # users
    for username in self.usernames:
        user: User = User.objects.create(username=username, password=username)
        user.set_password(user.username)  # !!!
        user.save()


@pytest.fixture
def setup_clients(
    request: pytest.FixtureRequest,
):
    self: BaseGameProperties = assert_base_class(request.instance)

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


@pytest.fixture
def setup_game(
    request: pytest.FixtureRequest,
):
    self: BaseGameProperties = assert_base_class(request.instance)
    self.game_pk = Game(players=self.users.values(), commit=True).pk


@pytest.fixture
def setup_game_by_api(
    request: pytest.FixtureRequest,
):
    self: BaseGameProperties = assert_base_class(request.instance)

    self.assert_response(
        'create game', 'vybornyy', 'POST', 'games', r'', status.HTTP_201_CREATED
    )
    # remember game pk to operate test data
    self.game_pk = self.response_data['id']  # type: ignore


@pytest.fixture
def setup_deck(request: pytest.FixtureRequest, deck_from_table_and_hands: CardList):
    self: BaseGameProperties = assert_base_class(request.instance)

    # check test arrange
    neccessary_amount = len(self.usernames) * DEFAULT.deal_cards_amount + sum(
        DEFAULT.flops_amounts
    )
    if deck_from_table_and_hands.length != neccessary_amount:
        pytest.skip('Current test deck intended for another players amount. ')

    # set our test deck to the game's default
    setattr(Decks, 'TEST_DECK', deck_from_table_and_hands)
    with temporally(DEFAULT, deck_container_name='TEST_DECK', deck_shuffling=False):
        yield
    delattr(Decks, 'TEST_DECK')


@pytest.fixture
def setup_users_banks(request: pytest.FixtureRequest):
    self: BaseGameProperties = assert_base_class(request.instance)

    banks: list[int] = []
    for i, u in enumerate(self.users_list):
        u.profile.bank = (i + 1) * 1000 + (i + 1) * 10
        u.profile.save()
        banks.append(u.profile.bank)

    self.input_users_bank = {name: bank for name, bank in zip(self.usernames, banks)}
    return banks


@pytest.fixture
def setup_expected_combos(
    request: pytest.FixtureRequest,
    table_and_hands_and_expected_combos,
):
    self: BaseGameProperties = assert_base_class(request.instance)

    combos: list[Combo] = table_and_hands_and_expected_combos['expected_combos']
    self.expected_combos = {}
    for user, combo in zip(self.users, combos, strict=True):
        self.expected_combos[user] = combo


@pytest.fixture
def setup_urls(request: pytest.FixtureRequest):
    self: BaseGameProperties = assert_base_class(request.instance)

    # format urls
    for key, url in self.urls.items():
        if '{game_pk}' in url:
            self.urls[key] = url.format(game_pk=self.game_pk)

    # check game data no errors
    self.game.full_clean()
