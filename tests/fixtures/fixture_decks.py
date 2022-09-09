from __future__ import annotations

import logging

import pytest
from _pytest.fixtures import SubRequest as PytestSubRequest
from core.functools.utils import get_func_name, init_logger, isinstance_items
from games.backends.cards import CardList
from games.backends.combos import CLASSIC_COMBOS, Combo, ComboStacks

logger = init_logger(__name__, logging.DEBUG)


@pytest.fixture(
    params=[
        pytest.param(
            dict(
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
                        {'rank': [CardList('5-c', '5-h')]},
                    ),
                ),
            ),
            id='simple test (3 players): the second one has winning combination',
        ),
        pytest.param(
            dict(
                table=CardList('Ace|H', 'Ace|D', 'King|C', '5-c', '7-s'),
                hands=(
                    CardList('10-s', '9-s'),
                    CardList('Ace|H', '2-h'),
                    CardList('2-c', '5-h'),
                    CardList('8-c', '9-h'),
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
                        {'rank': [CardList('5-c', '5-h')]},
                    ),
                    (
                        'high card',
                        {'high_card': [...]},
                    ),
                ),
            ),
            id='simple test (4 players): the second one has winning combination',
        ),
    ],
)
def table_and_hands_and_expected_combos(request: PytestSubRequest):
    logger.info(f'Fixture {get_func_name()} used.')

    data = request.param
    if isinstance_items(data['expected_combos'], list, Combo):
        logger.warning('Repeted re-format expected combos. Skip.')
        return data

    # re-arrange combos
    combos = []
    for expected_name, expected_cases in data['expected_combos']:
        stacks = ComboStacks()
        stacks.cases = expected_cases
        combos.append(Combo(CLASSIC_COMBOS.get(expected_name), stacks))
    data['expected_combos'] = combos
    return data


@pytest.fixture
def deck_from_table_and_hands(table_and_hands_and_expected_combos: dict):
    """Get custom deck from input data and set it as game deck."""
    logger.info(f'Fixture {get_func_name()} used.')

    data = table_and_hands_and_expected_combos
    table = data['table']
    hands = data['hands']

    # collect deck
    deck = CardList()
    deck.extend(table)
    for cards in zip(*reversed(hands), strict=True):
        deck.extend(cards)

    return deck
