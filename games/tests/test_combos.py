

import itertools
import random
from copy import deepcopy

import pytest

from games.backends.cards import Card, CardList, Stacks
from games.backends.combos import (CLASSIC_COMBOS, ComboKind, ComboKindList,
                            ComboStacks, Conditions)


@pytest.mark.parametrize('input_data, expected', [
    (CLASSIC_COMBOS,
     [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, ])
])
def test_combo_kind_list(input_data: ComboKindList, expected: list[float]):
    # print(*input_data, sep='\n')
    for combo, priority in zip(input_data, expected):
        assert combo.priority == priority


@pytest.mark.parametrize('input_data, expected_cases', [
    # 1- high card
    pytest.param(
        CardList(
            # input
            'J,h',
            '7,s',
            'K,c',
        ),
        {
            'highest card': [
                # expected
                CardList('K.c'),
                CardList('J.h'),
                CardList('7.s'),
            ],
        },
        id='01- high card'
    ),
    # 2- simple test
    pytest.param(
        CardList(
            # input
            'A,h', 'A,c',
            '10,h', '10,c', '10,d', '10.s',
            'K,c', 'K.c'
        ),
        {
            # expected
            'rank': [
                CardList('10.s', '10.h', '10,d', '10,c'),
                CardList('A,h', 'A,c'),
                CardList('K.c', 'K.c'),
            ],
            'suit': [
                CardList('A.c', 'K.c', 'K.c', '10.c'),
                CardList('A,h', '10.h'),
                # CardList('10,s'),  - no group
                # CardList('10,d'),  - no group
            ],
            'row': [
                CardList('A.h', 'K.c'),
            ],
            'highest card': [
                CardList('A,h'),
                CardList('A,c'),
                CardList('K,c'),
                CardList('K.c'),
                CardList('10.s'),
                CardList('10,h'),
                CardList('10,d'),
                CardList('10,c'),
            ],
        },
        id='02- simple test'
    ),
    # 3- add jokers
    pytest.param(
        CardList(
            # input
            'A.h', 'A.c',
            '10.h', '10.c', '10.d', '10.s',
            'K.c', 'K.c',
            'red', 'black'
        ),
        {
            # expected
            'rank': [
                CardList('10.s', 'black(10.s)', 'red(10.s)', '10.h', '10.d', '10.c'),
                CardList('A.h', 'A.c'),
                CardList('K.c', 'K.c'),
            ],
            'suit': [
                CardList('A.c', 'black(A|c)', 'red(A.c)', 'K.c', 'K.c', '10.c'),
                CardList('A.h', '10.h'),
                # CardList('10,s'),  - no group
                # CardList('10,d'),  - no group
            ],
            # 'row': [
            #     CardList('A.h', 'K.c', 'black(Q.s)', 'red(J.s)', '10.s'),
            # ],
            #'highest card': [],
        },
        id='03- add jokers'
    ),
    # 4- test row
    # 4 possible extrime values
    pytest.param(
        CardList(
            # input
            'red',
            'K.h',
            # not row
            '10.c',
            '3.h',
        ),
        {
            # expected
            'row': [
                CardList('red(A.s)', 'K.h'),
            ],
        },
        id='04- test row (possible extrime values)'
    ),
    # 5 possible extrime values
    pytest.param(
        CardList(
            # input
            'A.h', 'A.d',
            'red',
            # not row
            'J.c',
            '3.h',
        ),
        {
            # expected
            'row': [
                CardList('A.h', 'red(K.s)'),
            ],
        },
        id='05- test row (possible extrime values)'
    ),
    # possible extrime values
    pytest.param(
        CardList(
            # input
            '2.h',
            'red',
            # not row
            # 'A.c',
            # 'J.h',
        ),
        {
            # expected
            'row': [
                CardList('red(3.s)', '2.h'),
            ],
        },
        id='06- test row (possible extrime values)'
    ),
    # 4.4 possible extrime values - append many jokers
    pytest.param(
        CardList(
            # input
            '3.h',
            'red',
            'red',
            'red',
            'red',
            # not row
            # 'A.c',
            # 'J.h',
        ),
        {
            # expected
            'row': [
                CardList('red(7.s)', 'red(6.s)', 'red(5.s)', 'red(4.s)', '3.h'),
            ],
        },
        id='07- test row (possible extrime values - append many jokers)'
    ),
    # 4.5 possible extrime values
    pytest.param(
        CardList(
            # input
            '2.h',
            'red',
            '4.c',
            # not row
            'A.c',
            'J.h',
        ),
        {
            # expected
            'row': [
                CardList('4.c', 'red(3.s)', '2.h'),
            ],
        },
        id='08- test row (possible extrime values)'
    ),
    # 4.6 possible extrime values - 2 seq
    pytest.param(
        CardList(
            # input
            '2.h',
            'red',
            '4.c',
            '5.d',
            # --
            'K.c',
            'Q.h',
        ),
        {
            # expected
            'row': [
                CardList('5.d', '4.c', 'red(3.s)', '2.h'),
                CardList('K.c', 'Q.h',),
            ],
        },
        id='09- test row (possible extrime values - 2 seq)'
    ),
    # 4.7 possible extrime values - 2 seq and 2- jokers
    pytest.param(
        CardList(
            # input
            'black',
            'Q.h',
            'K.c',
            'red',
            '10.d',
            # --
            '5.d',
            '4.c',
            '2.h',
            # --
        ),
        {
            # expected
            'row': [
                CardList(
                    'black(A.s)',
                    'Q.h',
                    'K.c',
                    'red(J.d)',
                    '10.d',
                ),
                CardList(
                    '5.d',
                    '4.c',
                ),
            ],
        },
        marks=pytest.mark.xfail,
        id='10- have to drag the black joker forward instead of the red one'
    ),
    # row tail test
    # 11 basic
    pytest.param(
        CardList(
            # input
            'A.h',
            # -- no need here
            'Q.c',
            'red',
            '10.d',
            'black',  # -- joker here
            '8.h',
            '7.h',
            '6.h',
        ),
        {
            # expected
            'row': [
                CardList(
                    # 'A.h',
                    # -- no need here
                    'Q.c',
                    'black(J.s)',
                    '10.d',
                    'red(9.s)',  # -- joker here
                    '8.h',
                    '7.h',
                    '6.h',
                )
            ],
        },
        id='11- row tail test (basic)'
    ),
    # 12 no tail - [red, King, Quen]..[9][8]
    # -- (2) cards gap VS (1) joker -- case starts with Joker
    pytest.param(
        CardList(
            'red',
            'K.d',
            'Q.c',
            # 'Jack'
            # '10'
            '9.d',
            '8.h',
        ),
        {
            # expected
            'row': [
                CardList(
                    'red(A.s)',
                    'K.d',
                    'Q.c',
                    # 'Jack'
                    # '10'
                ),
                CardList(
                    '9.d',
                    '8.h',
                )
            ],
        },
        id='12- no tail - [red, King, Quen]..[9][8] -- (2) cards gap VS (1) joker'
    ),
    # 13 no tail - [Ace, King, red]..[10][9]
    # -- (2) cards gap VS (1) joker -- case ends with Joker
    pytest.param(
        CardList(
            'A.h',
            'K.d',
            'red',
            # 'Jack'
            '10.c',
            '9.d',
        ),
        {
            # expected
            'row': [
                CardList(
                    'A.h',
                    'K.d',
                    'red(Q.s)',
                    # 'Jack'
                ),
                CardList(
                    '10.c',
                    '9.d',
                )
            ],
        },
        id='13- no tail - [Ace, King, red]..[10][9] -- (2) cards gap VS (1) joker'
    ),
    # 14 no tail - [red, King, red].....[9]
    # -- (2) cards gap VS (1) joker -- case ends and start with Jokers
    pytest.param(
        CardList(
            'red',
            'K.d',
            'red',
            # 'Jack'
            # '10'
            '9.d',
        ),
        {
            # expected
            'row': [
                CardList(
                    'red(A.s)',
                    'K.d',
                    'red(Q.s)',
                    # 'Jack'
                    # '10'
                ),
            ],
        },
        id='14 no tail - [red, King, red].....[9] -- (2) cards gap VS (1) joker'
    ),
    # end test data
])
def test_combostacks_track(input_data: CardList, expected_cases: dict[str, Stacks]):
    # Arrange 1: randomize a little bit our input_data
    shuffeled = CardList(instance=input_data).shuffle()
    stacks: Stacks = [CardList()]
    for i, card in enumerate(shuffeled):
        stacks[-1].append(card)
        if i >= input_data.length / 2:
            stacks.append(CardList())
    # Act 1:
    combo = ComboStacks()
    combo.track(*stacks)
    # Assertion 1:
    for key in expected_cases:
        if key in combo.cases:
            assert combo.cases[key] == expected_cases[key]
        elif expected_cases[key] != []:
            assert False, (f'Expecting a {key} case after tracking.')

    # Arrange 2:
    new_card_instances = False
    for key in expected_cases:
        data: list[Card] = list(itertools.chain(*expected_cases[key]))
        random.shuffle(data)
        middle_index = int(len(data)/2)
        stacks = [
            CardList(*data[:middle_index], new_card_instances=new_card_instances),
            CardList(*data[middle_index:], new_card_instances=new_card_instances),
        ]
        # Act 2:
        random.shuffle(stacks)
        combo = ComboStacks()
        combo.track(*stacks)
        # Assertion 2: every card is the same
        for test_group, input_group in zip(
            combo.cases[key], expected_cases[key], strict=True
        ):
            assert test_group == input_group

            # # CANT PASS THIS TEST :(
            # # they should be the same cards..
            # for test_card, input_card in zip(test_group, input_group, strict=True):
            #     assert test_card is not input_card


@pytest.mark.parametrize('minor, expected, major', [
    pytest.param(
        CLASSIC_COMBOS.get('one pair'), True,
        {
            'rank': [3]
        },
        id='01'
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), True,
        {
            'rank': [3]
        },
        id='02'
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), True,
        {
            'rank': [3, 2]
        },
        id='03'
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), False,
        {
            'rank': [2, 2]
        },
        id=''
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), True,
        {
            'rank': [3],
            'row': [2]
        },
        id=''
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), False,
        {
            'rank': [2],
            'row': [100]
        },
        id=''
    ),
    pytest.param(
        CLASSIC_COMBOS.get('three of kind'), False,
        {
            'rank': [2, 2, 2, 2, 2],
            'row': [100]
        },
        id=''
    ),
    pytest.param(
        CLASSIC_COMBOS.get('straight flush'), True,
        {
            'suit': [5],
            'row': [5]
        },
        id=''
    ),
    pytest.param(
        CLASSIC_COMBOS.get('straight flush'), False,
        {
            'rank': [100],
            'suit': [5],
            'row': [4, 4, 4, 4, 4]
        },
        id=''
    ),
    pytest.param(
        ComboKind(rank_case=[3, 3], row_case=[3, 3]), False,
        {
            'rank': [3],
            'suit': [10, 10, 10],
            'row': [3, 3]
        },
        id=''
    ),
])
def test_combokind_is_minor_combo_for(
        minor: ComboKind,
        expected: bool,
        major: Conditions
        ):
    assert minor.is_minor_combo_for(major) == expected


@pytest.mark.parametrize('input_cases, ref, expected', [
    pytest.param(
        {
            'rank': [
                CardList('Ace|H', 'Ace|C', 'Ace|D', 'Ace|S'), CardList('K|H', 'K|C')
            ]
        },
        CLASSIC_COMBOS.get('three of kind'),
        {
            'rank': [CardList('Ace|H', 'Ace|C', 'Ace|D')]
        },
        id='01 base',
    ),
    pytest.param(
        {
            'rank': [CardList(), CardList()]
        },
        CLASSIC_COMBOS.get('three of kind'),
        {
            'rank': [CardList()]
        },
        id='02 empty stacks',
    ),
    pytest.param(
        {
            'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')]
        },
        CLASSIC_COMBOS.get('full house'),
        {
            'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')]
        },
        id='03 if nothing to trim -- trimed nothing',
    ),
    pytest.param(
        {
            'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
            'suit': [CardList('10|h', '10|d')]
        },
        CLASSIC_COMBOS.get('full house'),
        {
            'rank': [CardList('Ace|H', 'Ace|C'), CardList('K|H', 'K|C')],
        },
        id='04 but trimed excess cases `suit`',

    ),
])
def test_comokind_trim_to(
        input_cases: dict[str, Stacks],
        ref: ComboKind,
        expected: dict[str, Stacks]
        ):
    combo = ComboStacks()
    combo.cases = deepcopy(input_cases)
    combo.trim_to(ref)

    assert combo.cases == expected


@pytest.mark.parametrize('input_cases, expected', [
    pytest.param(
        {
            'rank': [CardList('Ace|H'), CardList('K|H', 'K|C')],
            'suit': [CardList('10|h', '10|d')]
        },
        AssertionError(),
        id='01 not sorted stacks',
    ),
])
def test_comokind_trim_to_exeptions(
        input_cases: dict[str, Stacks],
        expected: Exception
        ):
    try:
        combo = ComboStacks()
        combo.cases = deepcopy(input_cases)
        combo.trim_to(CLASSIC_COMBOS.get('full house'))
        assert False, ('AssertionError is not raised, but has to')
    except Exception as e:
        assert isinstance(e, type(expected))
        assert expected.args == e.args


@pytest.mark.parametrize('input_stacks, expected_combo, expected_cases', [
    pytest.param(
        [
            CardList('A|h'), CardList('A|d')
        ],
        CLASSIC_COMBOS.get('one pair'),
        {
            'rank': [CardList('A|h', 'A|d')]
        },
        id='01',
    ),
    pytest.param(
        [
            CardList(
                'A|h',
                'red',
                'Q|d',
                'J|d'
            ),
            CardList(
                '8|d',
                '7|s',
            ),
            CardList(
                '2|c',
                '2|h',
            ),
        ],
        CLASSIC_COMBOS.get('three of kind'),
        {
            'rank': [
                CardList(
                    'red(2|s)',
                    '2|h',
                    '2|c',
                )
            ]
        },
        id='02',
    ),
])
def test_track_and_merge(
        input_stacks: Stacks,
        expected_combo: ComboKind,
        expected_cases: dict[str, Stacks]
        ):
    random.shuffle(input_stacks)
    for cards in input_stacks:
        random.shuffle(cards)

    combo = ComboStacks()
    assert combo.track_and_merge(*input_stacks) == expected_combo
    assert combo.cases == expected_cases
