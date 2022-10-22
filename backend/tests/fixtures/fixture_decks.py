from __future__ import annotations

import itertools
import logging
from typing import Any

import pytest
from _pytest.fixtures import SubRequest as PytestSubRequest
from core.utils import get_func_name, init_logger, is_sorted
from games.configurations.configurations import DEFAULT_CONFIG
from games.services.cards import CardList
from games.services.combos import Combo, ComboStacks

from tests.tools import param_kwargs

logger = init_logger(__name__, logging.DEBUG)
DEFAULT_COMBOS = DEFAULT_CONFIG.combos


@pytest.fixture(
    params=[
        param_kwargs(
            '01- simple test (4 players)',
            table=['Ace|H', 'Ace|D', 'King|C', '5|C', '7|S'],
            hands=(
                ['Ace|H', '3|H'],  # winner: 3|h > 3|c
                ['Ace|H', '3|C'],  # 2nd place
                ['2|C', '5|H'],  # 3d olace
                ['10|S', '9|S'],  # looser
            ),
            rate_groups=([0], [1], [2], [3]),
            expected_combos=(
                ('three of kind', ['Ace|H', 'Ace|H', 'Ace|D']),
                ('three of kind', ['Ace|H', 'Ace|H', 'Ace|D']),
                ('two pair', ['Ace|H', 'Ace|D'] + ['5|C', '5|H']),
                ('one pair', ['Ace|H', 'Ace|D']),
            ),
        ),
        param_kwargs(
            '02- (the same) but two winners (4 players)',
            table=['Ace|H', 'Ace|D', 'King|C', '5|C', '7|S'],
            hands=(
                ['Ace|H', '9|H'],  # winner: 9|H == 9|H
                ['Ace|H', '9|H'],  # winner: 9|H == 9|H
                ['2|C', '5|H'],  # 2d olace
                ['10|S', '9|S'],  # looser
            ),
            rate_groups=([0, 1], [2], [3]),
            expected_combos=(
                ('three of kind', ['Ace|H', 'Ace|H', 'Ace|D']),
                ('three of kind', ['Ace|H', 'Ace|H', 'Ace|D']),
                ('two pair', ['Ace|H', 'Ace|D'] + ['5|C', '5|H']),
                ('one pair', ['Ace|H', 'Ace|D']),
            ),
        ),
    ],
)
def table_and_hands_and_expected_combos(request: PytestSubRequest):
    logger.info(f'Fixture {get_func_name()} used.')

    # Because diferent fixture could call for this one for one more time
    # but with the same request.param value, we have to initialize another dict data,
    # and leaves internal as it is.
    input_data: dict = request.param
    data: dict = {}
    data['rate_groups'] = input_data['rate_groups']
    data['table'] = CardList(*input_data['table'])
    data['hands'] = [CardList(*cards) for cards in input_data['hands']]

    # arrange combos
    combos = []
    for (expected_name, expected_combo_cards), hand in zip(input_data['expected_combos'], data['hands']):
        stacks = ComboStacks()
        kind = stacks.track_and_merge(
            hand,
            data['table'],
            references=DEFAULT_COMBOS,
            possible_highest=DEFAULT_CONFIG.deck.interval.max,
        )

        # pre-assertion for input data at fixture param
        expected: Any = DEFAULT_COMBOS.get(expected_name)
        assert kind == expected, 'invalid input test data'
        expected = CardList(*expected_combo_cards).sortby(reverse=True)
        assert CardList(*stacks.cases_chain) == expected, 'invalid input test data'

        combos.append(Combo(kind, stacks))

    # pre-assertion for input data at fixture param
    assert is_sorted(combos, reverse=True), 'combos must be provided in winning order'
    for (key, group), rate_group in zip(itertools.groupby(combos), data['rate_groups'], strict=True):
        assert len(list(group)) == len(rate_group), 'invalid rate_groups provided'

    data['expected_combos'] = combos
    return data
