import copy
from operator import eq, ge, gt, is_, is_not, le, lt, ne
from typing import Any, Callable

import pytest

from games.services.cards import Card, CardList, Decks, JokerCard, Stacks


@pytest.mark.parametrize(
    ['input_data', 'expected'],
    [
        ((Card(14, 1), Card(14, 1)), {is_: False, is_not: True, eq: True, ne: False}),
        (
            (Card('Ace|D'), Card('Ace|D')),
            {is_: False, is_not: True, eq: True, ne: False},
        ),
        ((Card(15, 'D'), Card('Ace', 4)), {lt: False, le: False, gt: True, ge: True}),
        ((Card('2|C'), Card('Ace|D')), {lt: True, le: True, gt: False, ge: False}),
        # spades более крутая масть, чем hearts
        ((Card('7|H'), Card('7|S')), {lt: True, le: True, gt: False, ge: False}),
        # проверим меньше или равно, больше или равно
        ((Card('Ace|D'), Card('Ace|D')), {lt: False, le: True, gt: False, ge: True}),
        # проверим Джокеров на ==
        (
            (JokerCard('red'), JokerCard('red')),
            {is_: False, is_not: True, eq: True, ne: False},
        ),
        # разные джокеры не равны | black != red
        (
            (JokerCard('red'), JokerCard('black')),
            {is_: False, is_not: True, eq: False, ne: True},
        ),
        # проверим одинаковых Джокеров на < <=  > >=
        (
            (
                JokerCard('red', reflection='Ace|H'),
                JokerCard('red', reflection='Ace|H'),
            ),
            {lt: False, le: True, gt: False, ge: True},
        ),
        # проверим разных Джокеров но с одинаковым зеркалом, они должны быть !=
        (
            (
                JokerCard('red', reflection='Ace|H'),
                JokerCard('black', reflection='Ace|H'),
            ),
            {is_: False, is_not: True, eq: False, ne: True},
        ),
        # black > red, если отражение (reflection) одинаковое
        (
            (
                JokerCard('black', reflection='Ace|H'),
                JokerCard('red', reflection='Ace|H'),
            ),
            {lt: False, le: False, gt: True, ge: True},
        ),
        # red < black, если отражение (reflection) одинаковое
        (
            (
                JokerCard('red', reflection='Ace|H'),
                JokerCard('black', reflection='Ace|H'),
            ),
            {lt: True, le: True, gt: False, ge: False},
        ),
        # проверим Джокеров (без зеркала) на < <=  > >=
        (
            (JokerCard('red'), JokerCard('black')),
            {
                lt: 'NotImplemented',
                le: 'NotImplemented',
                gt: 'NotImplemented',
                ge: 'NotImplemented',
            },
        ),
        # проверим Джокерa и карту на <
        (
            (JokerCard('red', reflection='Ace|H'), Card('King|C')),
            {lt: False, le: False, gt: True, ge: True},
        ),
        # проверим Джокерa и карту ==
        (
            (JokerCard('red', reflection='Ace|H'), Card('Ace|H')),
            {is_: False, is_not: True, eq: True, ne: False},
        ),
        # проверим Джокерa и карту на <=    ! they equel !
        (
            (JokerCard('red', reflection='Ace|H'), Card('Ace|H')),
            {lt: False, le: True, gt: False, ge: True},
        ),
    ],
)
def test_card_ordering(
    input_data: tuple[Card, Card], expected: dict[Callable[[Any, Any], bool], bool]
):
    for operator, result in expected.items():
        try:
            assert operator(input_data[0], input_data[1]) == result
        except TypeError:
            assert result == 'NotImplemented'


@pytest.mark.parametrize(
    'input_data, expected_len',
    [
        [CardList(), 0],
        [CardList(Card('Ace-D'), Card('King,H')), 2],
        [CardList(Card('Ace/D'), ('King-H')), 2],
        [CardList('(12,3)', 'King|H'), 2],
        [CardList('red', 'king|h'), 2],
        [CardList('red', 'black', '(12,H)', 'Quin|C'), 4],
    ],
)
def test_cardlist_init_len(input_data: CardList, expected_len: int):
    assert input_data.length == expected_len


@pytest.mark.parametrize(
    'cards, expected',
    [
        pytest.param(
            [''],
            0,
        ),
        pytest.param(
            ['(),.|-'],
            0,
        ),
    ],
)
def test_cardlist_init_by_str_cards(cards: list[str], expected: int):
    cl = CardList(*cards)
    assert len(cl) == expected


@pytest.mark.parametrize(
    'instance, expected',
    [
        pytest.param(
            '  ',
            CardList(),
        ),
        pytest.param(
            '    [    ]  ',
            CardList(),
        ),
        pytest.param(
            '    [  Ace-H,   10-D,    ]  ',
            CardList('Ace-H', '10-D'),
        ),
        pytest.param(
            '   11-1    ',
            CardList('Jack-Clubs'),
            id='init_by_integers_as_str_instances',
        ),
        pytest.param(
            '0-0', CardList(Card(0, 0)), id='01 init_by_integers_as_str_instances'
        ),
        pytest.param(
            '   [  A-1,    K-D,   ]   ',
            CardList('Ace|C', 'King|D'),
        ),
    ],
)
def test_cardlist_init_by_str_instance(instance: str, expected: CardList):
    cl = CardList(instance=instance)
    assert cl == expected


@pytest.mark.parametrize(
    'cards, expected',
    [
        pytest.param(
            [' '],
            AssertionError(
                'card contains space symbol, but it reserved for CardList seperator'
            ),
        ),
        pytest.param(
            ['Ace Hearts'],
            AssertionError(
                'card contains space symbol, but it reserved for CardList seperator'
            ),
        ),
        pytest.param(
            ['Ace', 'H'],
            ValueError(
                "not supported: card = 'Ace'\n",
                "not supported: rank='Ace' | suit=None",
                "not supported: kind='Ace'",
            ),
        ),
        pytest.param(
            ['red', 'Ace', 'H'],
            ValueError(
                "not supported: card = 'Ace'\n",
                "not supported: rank='Ace' | suit=None",
                "not supported: kind='Ace'",
            ),
        ),
        pytest.param(
            (['red', 'Ace', 'H'],),
            ValueError(
                "Invalid card type <class 'list'>. Can by <class 'str'>"
                "<class 'games.services.cards.Card'>"
                "<class 'games.services.cards.JokerCard'>. ",
                "Did you forget to unpack(*) list of cards? ",
                "card=['red', 'Ace', 'H'] in cards=(['red', 'Ace', 'H'],). ",
            ),
        ),
        pytest.param(
            ['[Ace-H]'],
            AssertionError(
                'card contains [] symbols, but it reserved for Stacks seperator'
            ),
        ),
        pytest.param(
            [' Ace-H '],
            AssertionError(
                'card contains space symbol, but it reserved for CardList seperator'
            ),
        ),
        # pytest.param(
        #     ['    [ Ace-H, red(10-d)  ]  [ black ]'],
        #     ValueError(),
        # ),
    ],
)
def test_cardlist_init_by_str_cards_raises(cards: list[str], expected: Exception):
    with pytest.raises(expected_exception=type(expected)) as exp_info:
        CardList(*cards)
    assert exp_info.value.args == expected.args


@pytest.mark.parametrize(
    'instance, expected',
    [
        pytest.param(
            '    Ace H    ',
            ValueError(
                "not supported: card = 'Ace'\n",
                "not supported: rank='Ace' | suit=None",
                "not supported: kind='Ace'",
            ),
        ),
        pytest.param(
            '  A-1, K-D,   ]',
            ValueError("invalid brackets `[` `]` at instance='  A-1, K-D,   ]'"),
        ),
    ],
)
def test_cardlist_init_by_str_instances_raises(instance: str, expected: Exception):
    with pytest.raises(expected_exception=type(expected)) as exp_info:
        CardList(instance=instance)
    assert exp_info.value.args == expected.args


@pytest.mark.parametrize(
    'input_data',
    [
        CardList('Ace|H', 'King|H', 'Quin|C'),
    ],
)
def test_cardlist_item_insances_behavior(input_data: CardList):
    # copy behavior
    new = input_data.copy()
    assert new == input_data
    assert new is not input_data
    assert new[0] == input_data[0]
    assert new[0] is input_data[0]  # becouse of shallow copy
    new = input_data.copy(deep=True)
    assert new[0] is not input_data[0]  # becouse of deep copy

    new_shallow = copy.copy(input_data)
    assert new_shallow == input_data
    assert new_shallow is not input_data
    assert new_shallow[0] == input_data[0]
    assert new_shallow[0] is input_data[0]  # becouse of shallow copy

    # append do NOT create new card object
    card = Card('Ace|H')
    cl = CardList()
    cl.append(card)
    assert cl[0] == card
    assert cl[0] is card

    # also __init__
    assert CardList(card)[0] == card
    assert CardList(card)[0] is card

    # but you can specify reverse
    assert CardList(card, new_card_instances=True)[0] == card
    assert CardList(card, new_card_instances=True)[0] is not card

    # slice do not and you can not specify that
    assert input_data[:][0] == input_data[0]
    assert input_data[:][0] is input_data[0]

    # extend also do not
    cl = CardList('2|h', '3|c')
    cl.extend(input_data)
    assert cl[-1] == input_data[-1]
    assert cl[-1] is input_data[-1]

    # type cheking
    assert isinstance(input_data[:], CardList)


@pytest.mark.parametrize(
    'input_data, reverse',
    [
        (
            CardList(
                '10.s',
                'black(10.s)',
                'red(10.s)',
                '10.d',
                'red(6.h)',
                'red(6.d)',
                'black',
                'red',
            ),
            True,
        ),
        pytest.param(
            CardList(
                '10.s',
                'black(10.s)',
                'red(10.s)',
                '10.d',
                'red(6.h)',
                'red(6.d)',
                'black',
                'red',
            ),
            False,
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_sortby_jokers_behavior(input_data: CardList, reverse: bool):
    sorted_data = input_data.copy().shuffle().sortby('rank', reverse=reverse)

    assert sorted_data == input_data
    # Assertion: every card is the same
    for test_card, input_card in zip(sorted_data, input_data, strict=True):
        assert test_card is input_card


@pytest.mark.parametrize(
    'input_data, expected_list, expected_jokers',
    [
        (
            CardList(
                'red', 'A|s', 'K|s', 'K|c', '10|h', '2|c', 'black', '2|d', 'red(J|c)'
            ),
            CardList(
                'A|s',
                'K|s',
                'K|c',
                'red(J|c)',
                '10|h',
                '2|d',
                '2|c',
            ),
            CardList('red', 'black'),
        ),
    ],
)
def test_isolate_jokers(
    input_data: CardList, expected_list: CardList, expected_jokers: CardList
):
    input_data.shuffle()
    # straight check
    result = input_data.copy().isolate_jokers(sort_attr='rank')
    assert result == (expected_list, expected_jokers)
    # так же проверим, что все в исходном листе не осталось джокеров
    input_data.isolate_jokers(sort_attr='rank')
    assert not [c for c in input_data if c.is_joker and not c.is_mirror]


@pytest.mark.parametrize(
    'input_data, expected_list, expected_jokers',
    [
        pytest.param(
            CardList(
                'red', 'A|s', 'K|s', 'K|c', '10|h', '2|c', 'black', '2|d', 'red(J|c)'
            ),
            CardList(
                'A|s',
                'K|s',
                'K|c',
                'red(J|c)',
                '10|h',
                '2|d',
                '2|c',
            ),
            CardList('red', 'black'),
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_isolate_jokers_reverse(
    input_data: CardList, expected_list: CardList, expected_jokers: CardList
):
    input_data.shuffle()
    # check reverse
    result = input_data.copy().isolate_jokers(sort_attr='rank', sort_reverse=False)
    assert result == (list(reversed(expected_list)), list(reversed(expected_jokers)))


@pytest.mark.parametrize(
    'input_data, expected',
    [
        (
            CardList(
                'A|h',
                'A|s',
                'K|s',
                'K|c',
                '10|h',
                '2|c',
                '2|d',
                '2|d',
            ),
            {
                'rank': [
                    CardList('A|s', 'A|h'),  # spades > hearts
                    CardList('K|s', 'K|c'),
                    CardList('10|h'),
                    CardList('2|d', '2|d', '2|c'),
                ],
                'suit': [
                    CardList('A|s', 'K|s'),
                    CardList('A|h', '10|h'),
                    CardList('2|d', '2|d'),
                    CardList('K|c', '2|c'),
                ],
            },
        ),
        # add mirrored jokers
        (
            CardList(
                'red(A|h)',
                'A|s',
                'K|s',
                'K|c',
                '10|h',
                '2|c',
                JokerCard('red', reflection='2|d'),
                '2|d',
            ),
            {
                'rank': [
                    CardList('A|s', 'red(A|h)'),
                    CardList('K|s', 'K|c'),
                    CardList('10|h'),
                    CardList('2|d', JokerCard('red', reflection='2|d'), '2|c'),
                ],
                'suit': [
                    CardList('A|s', 'K|s'),
                    CardList(JokerCard('red', reflection='A|h'), '10|h'),
                    CardList('2|d', JokerCard('red', reflection='2|d')),
                    CardList('K|c', '2|c'),
                ],
            },
        ),
        # add mirrored jokers in other places
        (
            CardList(
                JokerCard('red', reflection='A|h'),
                'A|s',
                'K|s',
                'K|c',
                '10|h',
                '2|c',
                '2|d',
                JokerCard('red', reflection='2|d'),
            ),
            {
                'rank': [
                    CardList('A|s', JokerCard('red', reflection='A|h')),
                    CardList('K|s', 'K|c'),
                    CardList('10|h'),
                    CardList('2|d', JokerCard('red', reflection='2|d'), '2|c'),
                ],
                'suit': [
                    CardList('A|s', 'K|s'),
                    CardList(JokerCard('red', reflection='A|h'), '10|h'),
                    CardList('2|d', JokerCard('red', reflection='2|d')),
                    CardList('K|c', '2|c'),
                ],
            },
        ),
        # add mirrored jokers with different ranks
        (
            CardList(
                JokerCard('red', reflection='A|h'),
                'A|s',
                'K|s',
                'K|c',
                '10|h',
                '2|c',
                JokerCard('red', reflection='2|d'),
                JokerCard('black', reflection='2|d'),
            ),
            {
                'rank': [
                    CardList('A|s', JokerCard('red', reflection='A|h')),
                    CardList('K|s', 'K|c'),
                    CardList('10|h'),
                    CardList(
                        JokerCard('black', reflection='2|d'),
                        JokerCard('red', reflection='2|d'),
                        '2|c',
                    ),
                ],
                'suit': [
                    CardList('A|s', 'K|s'),
                    CardList(JokerCard('red', reflection='A|h'), '10|h'),
                    CardList(
                        JokerCard('black', reflection='2|d'),
                        JokerCard('red', reflection='2|d'),
                    ),
                    CardList('K|c', '2|c'),
                ],
            },
        ),
        # add NOT mirrored jokers
        (
            CardList(
                JokerCard('red'),
                'A|s',
                'K|s',
                'K|c',
                '10|h',
                '2|c',
                JokerCard('black'),
                '2|d',
                JokerCard('red'),
            ),
            {
                'rank': [
                    CardList('A|s'),
                    CardList('K|s', 'K|c'),
                    CardList('10|h'),
                    CardList('2|d', '2|c'),
                    CardList('black', 'red', 'red'),
                ],
                'suit': [
                    CardList('A|s', 'K|s'),
                    CardList('10|h'),
                    CardList('2|d'),
                    CardList('K|c', '2|c'),
                    CardList('black', 'red', 'red'),
                ],
            },
        ),
    ],
)
def test_cardlist_groupby(input_data: CardList, expected: dict[str, Stacks]):
    for _ in range(2):
        for key in expected:
            for i, groupby_result in enumerate(input_data.groupby(key)):
                # groupby -> tuple[is_jkrs, CardList]
                group: CardList = groupby_result[1]
                expected_group = expected[key][i]

                assert group == expected_group
                # так же тип каждой карты должен совпадать
                assert all(map(lambda x, y: type(x) is type(y), group, expected_group))

        # and after shuffeling also
        input_data.shuffle()


def test_standart_52_card_deck_plus_jokers():
    jokers_amount = 5

    generator = Decks.standart_52_card_deck_plus_jokers(jokers_amount)
    cl = CardList(instance=generator)
    assert cl.length == 52 + jokers_amount

    # check joker kind amounts
    red = JokerCard('red')
    black = JokerCard('black')
    assert len(list(filter(lambda c: c == red, cl))) == 2
    assert len(list(filter(lambda c: c == black, cl))) == 3

    # check generator for not exhausness
    new_generator = Decks.standart_52_card_deck_plus_jokers(jokers_amount)
    assert CardList(instance=new_generator).length == 52 + jokers_amount

    # use new_generator again
    # be carefull, becouse in that way no cards will be yield
    assert CardList(instance=new_generator).length == 0
