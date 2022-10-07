import pytest
from _pytest.fixtures import SubRequest as PytestSubRequest

from games.services.cards import CardList, Stacks

from tests.tools import param_kwargs


@pytest.fixture(
    params=[
        param_kwargs(
            '01- high card',
            input_cards=[
                'J,h',
                '7,s',
                'K,c',
            ],
            expected_cases={},
        ),
        param_kwargs(
            '2- simple test',
            input_cards=[
                'A,h',
                'A,c',
                '10,h',
                '10,c',
                '10,d',
                '10.s',
                'K,c',
                'K.c',
            ],
            expected_cases={
                'rank': [
                    CardList('10.s', '10.h', '10,d', '10,c'),
                    CardList('A,h', 'A,c'),
                    CardList('K.c', 'K.c'),
                ],
                'suit': [
                    CardList('A.c', 'K.c', 'K.c', '10.c'),
                    CardList('A,h', '10.h'),
                ],
                'row': [
                    CardList('A.h', 'K.c'),
                ],
            },
        ),
        param_kwargs(
            '03- add jokers',
            input_cards=[
                # input
                'A.h',
                'A.c',
                '10.h',
                '10.c',
                '10.d',
                '10.s',
                'K.c',
                'K.c',
                'red',
                'black',
            ],
            expected_cases={
                'rank': [
                    CardList(
                        '10.s', 'black(10.s)', 'red(10.s)', '10.h', '10.d', '10.c'
                    ),
                    CardList('A.h', 'A.c'),
                    CardList('K.c', 'K.c'),
                ],
                'suit': [
                    CardList('A.c', 'black(A|c)', 'red(A.c)', 'K.c', 'K.c', '10.c'),
                    CardList('A.h', '10.h'),
                ],
                'row': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '04- test row (possible extrime values)',
            input_cards=[
                'red',
                'K.h',
                # not row
                '10.c',
                '3.h',
            ],
            expected_cases={
                'row': [
                    CardList('red(A.s)', 'K.h'),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '05- test row (possible extrime values)',
            input_cards=[
                'A.h',
                'A.d',
                'red',
                # not row
                'J.c',
                '3.h',
            ],
            expected_cases={
                'row': [
                    CardList('A.h', 'red(K.s)'),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '06- test row (possible extrime values)',
            input_cards=[
                '2.h',
                'red',
                # not row
                # 'A.c',
                # 'J.h',
            ],
            expected_cases={
                'row': [
                    CardList('red(3.s)', '2.h'),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '07- test row (possible extrime values - append many jokers)',
            input_cards=[
                '3.h',
                'red',
                'red',
                'red',
                'red',
                # not row
                # 'A.c',
                # 'J.h',
            ],
            expected_cases={
                'row': [
                    CardList(
                        'red(7.s)',
                        'red(6.s)',
                        'red(5.s)',
                        'red(4.s)',
                        '3.h',
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '08- test row (possible extrime values)',
            input_cards=[
                '2.h',
                'red',
                '4.c',
                # not row
                'A.c',
                'J.h',
            ],
            expected_cases={
                'row': [
                    CardList(
                        '4.c',
                        'red(3.s)',
                        '2.h',
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '09- test row (possible extrime values - 2 seq)',
            input_cards=[
                '2.h',
                'red',
                '4.c',
                '5.d',
                # --
                'K.c',
                'Q.h',
            ],
            expected_cases={
                'row': [
                    CardList(
                        '5.d',
                        '4.c',
                        'red(3.s)',
                        '2.h',
                    ),
                    CardList(
                        'K.c',
                        'Q.h',
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '10- possible extrime values - 2 seq and 2- jokers'
            '!! NEED NOT FIX !! have to drag the black joker forward instead of the red one',
            pytest.mark.xfail,
            input_cards=[
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
            ],
            expected_cases={
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
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '11- row tail test (basic)',
            input_cards=[
                'A.h',
                # -- no need here
                'Q.c',
                'red',
                '10.d',
                'black',  # -- joker here
                '8.h',
                '7.h',
                '6.h',
            ],
            expected_cases={
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
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '12- no tail - [red, King, Quen]..[9][8] -- (2) cards gap VS (1) joker  -- case starts with Joker',
            input_cards=[
                'red',
                'K.d',
                'Q.c',
                # 'Jack'
                # '10'
                '9.d',
                '8.h',
            ],
            expected_cases={
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
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '13- no tail - [Ace, King, red]..[10][9] -- (2) cards gap VS (1) joker -- case ends with Joker',
            input_cards=[
                'A.h',
                'K.d',
                'red',
                # 'Jack'
                '10.c',
                '9.d',
            ],
            expected_cases={
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
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
        param_kwargs(
            '14 no tail - [red, King, red].....[9] -- (2) cards gap VS (1) joker -- case ends and start with Jokers',
            input_cards=[
                'red',
                'K.d',
                'red',
                # 'Jack'
                # '10'
                '9.d',
            ],
            expected_cases={
                'row': [
                    CardList(
                        'red(A.s)',
                        'K.d',
                        'red(Q.s)',
                        # 'Jack'
                        # '10'
                    ),
                ],
                'suit': pytest.mark.skip,
                'rank': pytest.mark.skip,
            },
        ),
    ]
)
def tracking_cards_and_expected_cases(request: PytestSubRequest):
    input_cards: CardList = CardList(*request.param['input_cards'])

    # randomize a little bit our input_data
    shuffeled = CardList(instance=input_cards).shuffle()
    stacks: Stacks = [CardList()]
    for i, card in enumerate(shuffeled):
        stacks[-1].append(card)
        if i >= input_cards.length / 2:
            stacks.append(CardList())

    expected_cases: dict[str, Stacks] = request.param['expected_cases']
    return stacks, expected_cases
