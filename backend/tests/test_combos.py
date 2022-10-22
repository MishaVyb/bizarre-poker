import itertools
import operator
import random
from copy import deepcopy
from typing import Callable

import pytest
from games.configurations.configurations import DEFAULT_CONFIG
from games.services.cards import CardList, Stacks
from games.services.combos import (Combo, ComboKind, ComboKindList,
                                   ComboStacks, Conditions)

from tests.tools import param_kwargs_list

DEFAULT_COMBOS = ComboKindList(
    [
        ComboKind(highest_card=[1], name='high card'),
        ComboKind(rank=[2], name='one pair'),
        ComboKind(rank=[2, 2], name='two pair'),
        ComboKind(rank=[3], name='three of kind'),
        ComboKind(row=[5], name='straight'),
        ComboKind(suit=[5], name='flush'),
        ComboKind(rank=[3, 2], name='full house'),
        ComboKind(rank=[4], name='four of kind'),
        ComboKind(row=[5], suit=[5], name='straight flush'),
        ComboKind(rank=[5], name='pocker'),
    ]
)

@pytest.mark.parametrize(
    'input_data, expected',
    [
        (
            DEFAULT_COMBOS,
            [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90],
        )
    ],
)
def test_classic_combos_priority(input_data: ComboKindList, expected: list[float]):
    for combo, priority in zip(input_data, expected):
        assert combo.priority == priority


def test_combostacks_track(tracking_cards_and_expected_cases: tuple[Stacks, dict[str, Stacks]]):
    stacks, expected_cases = tracking_cards_and_expected_cases

    # arrange:
    combo = ComboStacks()
    combo.source = CardList(instance=itertools.chain(*stacks))

    # act:
    combo.track()

    # assert:
    for key in expected_cases:
        if expected_cases[key] == pytest.mark.skip:
            continue
        assert key in combo.cases, f'Expecting a {key} case after tracking.'
        assert combo.cases[key] == expected_cases[key]

    for key in combo.cases:
        if expected_cases.get(key) == pytest.mark.skip:
            continue
        assert key in expected_cases, f'Get unexpetced {key} case after tracking.'


@pytest.mark.parametrize(
    'minor, expected, major',
    [
        pytest.param(
            DEFAULT_COMBOS.get('one pair'),
            True,
            {'rank': [3]},
            id='01',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            True,
            {'rank': [3]},
            id='02',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            True,
            {'rank': [3, 2]},
            id='03',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            False,
            {'rank': [2, 2]},
            id='',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            True,
            {'rank': [3], 'row': [2]},
            id='',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            False,
            {'rank': [2], 'row': [100]},
            id='',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('three of kind'),
            False,
            {'rank': [2, 2, 2, 2, 2], 'row': [100]},
            id='',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('straight flush'),
            True,
            {'suit': [5], 'row': [5]},
            id='',
        ),
        pytest.param(
            DEFAULT_COMBOS.get('straight flush'),
            False,
            {'rank': [100], 'suit': [5], 'row': [4, 4, 4, 4, 4]},
            id='',
        ),
        pytest.param(
            ComboKind(rank=[3, 3], row=[3, 3]),
            False,
            {'rank': [3], 'suit': [10, 10, 10], 'row': [3, 3]},
            id='',
        ),
    ],
)
def test_combokind_is_minor_combo_for(minor: ComboKind, expected: bool, major: Conditions):
    assert minor.is_minor_combo_for(major) == expected


@pytest.mark.parametrize(
    'input_cases, ref, expected',
    [
        pytest.param(
            {
                'rank': [
                    CardList('Ace|H', 'Ace|C', 'Ace|D', 'Ace|S'),
                    CardList('K|H', 'K|C'),
                ]
            },
            DEFAULT_COMBOS.get('three of kind'),
            {
                'rank': [CardList('Ace|H', 'Ace|C', 'Ace|D')],
            },
            id='01 base',
        ),
        pytest.param(
            {
                'rank': [CardList(), CardList()],
            },
            DEFAULT_COMBOS.get('three of kind'),
            {
                'rank': [CardList()],
            },
            id='02 empty stacks',
        ),
        pytest.param(
            {
                'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
            },
            DEFAULT_COMBOS.get('full house'),
            {
                'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
            },
            id='03 if nothing to trim -- trimed nothing',
        ),
        pytest.param(
            {
                'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
                'suit': [CardList('10|h', '10|d')],
            },
            DEFAULT_COMBOS.get('full house'),
            {
                'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
            },
            id='04 but trimed excess cases `suit`',
        ),
    ],
)
def test_combokind_trim_to(input_cases: dict[str, Stacks], ref: ComboKind, expected: dict[str, Stacks]):
    combo = ComboStacks()
    combo.cases = deepcopy(input_cases)
    combo.trim_to(ref)

    assert combo.cases == expected


@pytest.mark.parametrize(
    'input_cases',
    [
        pytest.param(
            {
                'rank': [CardList('Ace|H'), CardList('K|H', 'K|C')],
                'suit': [CardList('10|h', '10|d')],
            },
            id='01 not sorted  stacks cases',
        ),
    ],
)
def test_combokind_trim_to_raises(input_cases: dict[str, Stacks]):
    with pytest.raises(AssertionError):
        combo = ComboStacks()
        combo.cases = deepcopy(input_cases)
        combo.trim_to(DEFAULT_COMBOS.get('full house'))


@pytest.mark.parametrize(
    'input_stacks, expected_kind, expected_cases',
    [
        pytest.param(
            [
                CardList('A|h'),
                CardList('A|d'),
            ],
            DEFAULT_COMBOS.get('one pair'),
            {
                'rank': [CardList('A|h', 'A|d')],
            },
            id='01 one pair',
        ),
        pytest.param(
            [
                CardList('A|h', 'red', 'Q|d', 'J|d'),
                CardList('8|d', '7|s'),
                CardList('2|c', '2|h'),
            ],
            DEFAULT_COMBOS.get('three of kind'),
            {
                'rank': [
                    CardList('red(2|s)', '2|h', '2|c'),
                ]
            },
            id='02 three of kind',
        ),
        pytest.param(
            [
                CardList('A|h'),
                CardList('10|d'),
            ],
            DEFAULT_COMBOS.get('high card'),
            {
                'highest_card': [CardList('A|h')],
            },
            id='03 - high card',
        ),
        pytest.param(
            [
                CardList('red', 'red'),
                CardList('black', 'black', 'black'),
            ],
            DEFAULT_COMBOS.get('pocker'),
            {
                'rank': [
                    CardList(
                        'black(A|s)',
                        'black(A|s)',
                        'black(A|s)',
                        'red(A|s)',
                        'red(A|s)',
                    )
                ],
            },
            id='04 - only jokers',
        ),
        pytest.param(
            [CardList('red')],
            DEFAULT_COMBOS.get('high card'),
            {
                'highest_card': [
                    CardList(
                        'red(A|s)',
                    )
                ],
            },
            id='04 - only_one_joker',
        ),
    ],
)
def test_track_and_merge(input_stacks: Stacks, expected_kind: ComboKind, expected_cases: dict[str, Stacks]):
    print('\n')
    random.shuffle(input_stacks)
    for cards in input_stacks:
        random.shuffle(cards)

    stacks = ComboStacks()
    kind = stacks.track_and_merge(
        *input_stacks,
        references=DEFAULT_COMBOS,
        possible_highest=DEFAULT_CONFIG.deck.interval.max,
    )

    # assert kind
    assert kind == expected_kind

    # assert stacks
    assert stacks.cases == expected_cases
    # check total equality!
    # for example: Ace|S == red(Ace|S) because of game logic
    # but for clean test we should check type equality between result and expected
    expected_cases_chain = itertools.chain(*itertools.chain(*expected_cases.values()))
    for a, b in zip(stacks.cases_chain, expected_cases_chain):
        assert type(a) == type(b)


@pytest.mark.parametrize(
    'cases, expected',
    [
        pytest.param(
            {'rank': [CardList('A|h', 'A|d')]},
            True,
            id='01',
        ),
        pytest.param(
            {},
            False,
            id='01',
        ),
        pytest.param(
            {
                'rank': [],
                'suit': [],
                'row': [],
                'highest_card': [],
            },
            False,
            id='01',
        ),
        pytest.param(
            {
                'rank': [CardList(), CardList()],
                'suit': [],
                'row': [CardList(), CardList(), CardList()],
                'highest_card': [],
            },
            False,
            id='01',
        ),
    ],
)
def test_combokind_bool(cases: dict[str, Stacks], expected: bool):
    combo = ComboStacks()
    combo.cases = cases
    assert bool(combo) == expected


@pytest.mark.parametrize(
    'left_cardlist, right_cardlist, comparision_kind, comparision_stacks, comparision_combo',
    [
        param_kwargs_list(
            '01- greatest high card. ',
            left_cardlist=['Ace|H'] + ['10|D'],
            right_cardlist=['K|H'] + ['Q|D'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
        param_kwargs_list(
            '02-equal high card. ',
            left_cardlist=['Ace|H'] + ['10|D'],
            right_cardlist=['Ace|H'] + ['10|D'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.eq,
            comparison_combo=operator.eq,
        ),
        param_kwargs_list(
            '03-equal high card but deferent others: 9|S > 9|C. ',
            left_cardlist=['Ace|H'] + ['10|D', '9|S'],
            right_cardlist=['Ace|H'] + ['10|D', '9|C'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
        param_kwargs_list(
            '04-equal-high-card-with-jokers',
            left_cardlist=['Ace|S'],
            right_cardlist=['red'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.eq,
            comparison_combo=operator.eq,
        ),
        param_kwargs_list(
            '05-big high card vs small pair. ',
            left_cardlist=['Ace|S'] + ['2|D'],  # high card combo
            right_cardlist=['red', '2|D'],  # pair combo
            comparison_kind=operator.lt,
            comparison_stacks=(
                operator.lt,
                NotImplemented,  # because of different cases lists (conditions)
            ),
            comparison_combo=operator.lt,
        ),
        param_kwargs_list(
            '06-street vs street. Kinds is equals, but Combos is not. ',
            left_cardlist=['14|S', '13|D', '12|H', '11|S', '10|S'],
            right_cardlist=['13|D', '12|H', '11|S', '10|S', '9|S'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
        param_kwargs_list(
            '07-street vs street. Ace SPADES vs Ace HEARTS. Highest card in combo has '
            'higher suit and it doesn`t matter if other cards has smaller. ',
            left_cardlist=['14|S', '13|C', '12|C', '11|C', '10|C'],
            right_cardlist=['14|H', '13|S', '12|S', '11|S', '10|S'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
        param_kwargs_list(
            '08-three of kind vs three of kind + different hands.',
            left_cardlist=['King|H', 'King|S', 'King|C'] + ['Ace|D'],
            right_cardlist=['King|H', 'King|S', 'King|C'] + ['10|D'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
        param_kwargs_list(
            # yes, here could be a special logic for comparing such cases
            # but it not obvious and we has no needs for that, so leave it NotImplemented
            '09- different len or cards at hands -- error. ',
            left_cardlist=['King|H', 'King|S', 'King|C'] + ['Ace|D', '10|D'],
            right_cardlist=['King|H', 'King|S', 'King|C'] + ['10|D'],
            comparison_kind=operator.eq,
            comparison_stacks=(operator.gt, NotImplemented),
            comparison_combo=(operator.gt, NotImplemented),
        ),
        param_kwargs_list(
            '10-pair vs pair. left pair smaller then right one and it doen`t matter '
            'about other cards (Ace|D and 3|D).',
            left_cardlist=['2|H', '2|S'] + ['Ace|D'],
            right_cardlist=['3|H', '3|S'] + ['10|D'],
            comparison_kind=operator.eq,
            comparison_stacks=operator.gt,
            comparison_combo=operator.gt,
        ),
    ],
)
def test_combo_comparison(
    left_cardlist: CardList,
    right_cardlist: CardList,
    comparision_kind: Callable,
    comparision_stacks: Callable | tuple[Callable, object],
    comparision_combo: Callable,
):
    # arrange (convert types) and randomize a little
    left_cardlist = CardList(*left_cardlist).shuffle()
    right_cardlist = CardList(*right_cardlist).shuffle()

    # act
    left_stacks = ComboStacks()
    left_kind = left_stacks.track_and_merge(
        left_cardlist,
        references=DEFAULT_COMBOS,
        possible_highest=DEFAULT_CONFIG.deck.interval.max,
    )
    left = Combo(left_kind, left_stacks)

    right_stacks = ComboStacks()
    right_kind = right_stacks.track_and_merge(
        right_cardlist,
        references=DEFAULT_COMBOS,
        possible_highest=DEFAULT_CONFIG.deck.interval.max,
    )
    right = Combo(right_kind, right_stacks)

    # assert
    for comparision, a, b in zip(
        [comparision_kind, comparision_stacks, comparision_combo],
        [left_kind, left_stacks, left],
        [right_kind, right_stacks, right],
    ):
        if not callable(comparision):
            if comparision[1] is NotImplemented:
                with pytest.raises(TypeError, match=r'not supported between instances'):
                    assert comparision[0](a, b)
            else:
                raise RuntimeError('Invalid input test data structure. ')
        else:
            assert comparision(a, b)
