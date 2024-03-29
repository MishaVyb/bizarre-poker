"""
Modul for interactions with gaming cards.

Card - jast a card
CardList - list of cards
Stacks - list of CardLists

Cards comparision.
Be careful with comparison mirrored jokers:

1. In first place we compare rank and suit.
>>> JokerCard('black', reflection='A|h') == Card('A|h')
True

2. Secondly, Red and Black Jokers are not equls even if they have the same(!) reflection
>>> black = JokerCard('black', reflection='A|h')
>>> red = JokerCard('red', reflection='A|h')
>>> black == red
False

3. And finally. black('A|h') < Card('A|h) -> False, because they are equal. But while
soring we suply extra key condition to achive result where just simple card worth more
then joker reflected that card. Have a look at CardList.sortby() implementation for more
details.

Cards string representation.
You can change default way for string representation by choosing a relevant method.
It also ovveride repr_method for JokerCard:
>>> Card.Text.repr_method = 'eng_short_suit'

"""

from __future__ import annotations

import functools
import itertools
import random
from operator import attrgetter
from typing import TYPE_CHECKING, ClassVar, Generator, Iterable, SupportsIndex, TypeAlias, overload

from core.utils import eq_first, init_logger, range_inclusevly, split

if TYPE_CHECKING:
    from games.configurations import DeckConfig


logger = init_logger(__name__)

SET_JOKERS_AFTER_EQUAL_CARD = True
"""
Flagg that define a specyfic way of sorting, when mirrored jokers placed after card with
other things being equal.
"""


class EmptyValueError(Exception):
    pass


@functools.total_ordering
class Card:
    """
    Describs card's rank and suid.

    Possible values:
    - rank: `14` (Ace), `13` (King), ... `3` (Three) or `2` (Two)
    - suit: `4` (Spades), `3` (Hearts), `2` (Diamonds) or `1` (Clubs)
    """

    class Text:
        """Handling Card text style.
        Redefine class varable `str_method` or `repr_method` to apply changes.
        Relevant methods: `default` `emoji` `eng_short_suit` `classic` `emoji_shirt`.

        Notice, that it also get affect for JokerCard because of inheritance.

        `str_method`
            default is `None` (for None __str__ calls __repr__ instead)
        `repr_method`
            default is `emoji` (better for representatins while debuging)
        """

        _METHODS = (
            'default',
            'eng_short_suit',
            'eng_shirt',
            'emoji',
            'emoji_shirt',
            'classic',
            'classic_shirt',
            None,
        )

        EMOJI: ClassVar = {
            'rank': ['[not def]', '[not def]', '2️⃣ ', '3️⃣ ', '4️⃣ ', '5️⃣ ', '6️⃣ ', '7️⃣ ', '8️⃣ ', '9️⃣ ', '🔟', 'J', 'Q', 'K', 'A'],  # fmt: skip
            'suit': ['[not def]', '➕', '🔺', '💔', '🖤'],
            'shirt': ['🎴'],
        }
        ENG: ClassVar = {
            'rank': ['[not def]', '[not def]', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace'],  # fmt: skip
            'suit': ['[not def]', 'Clubs', 'Diamonds', 'Hearts', 'Spades'],
            'shirt': ['*'],
        }
        CLASSIC: ClassVar = {
            'rank': ['[not def]', '[not def]', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],  # fmt: skip
            'suit': ['[not def]', '♣️', '♦️', '♥️', '♠️'],
            'shirt': None,
        }

        str_method: ClassVar[str | None] = None
        repr_method: ClassVar[str] = 'emoji'

        @classmethod
        def get_repr(cls, c: Card, method_name: str | None = None) -> str:
            method_name = method_name or cls.repr_method
            assert method_name in cls._METHODS, f'invalind {method_name=}'
            try:
                return getattr(cls, method_name)(c)
            except IndexError:
                return cls.default(c)

        @classmethod
        def get_str(cls, c: Card, method_name: str | None = None) -> str:
            method_name = method_name or cls.str_method
            assert method_name in cls._METHODS, f'invalid {method_name=}'
            try:
                return getattr(cls, method_name or cls.repr_method)(c)
            except IndexError:
                return cls.default(c)

        @staticmethod
        def get_rank_value(rank_english: str) -> int:
            try:
                return Card.Text.ENG['rank'].index(rank_english)
            except ValueError:
                raise ValueError(f'not supported card rank: {rank_english}')

        @staticmethod
        def get_suit_value(suit_english: str) -> int:
            try:
                return Card.Text.ENG['suit'].index(suit_english)
            except ValueError:
                raise ValueError(f'not supported card rank: {suit_english}')

        @staticmethod
        def default(c: Card) -> str:
            return f'Card({c.rank}, {c.suit})'

        @staticmethod
        def emoji(c: Card) -> str:
            return Card.Text.EMOJI['rank'][c.rank] + Card.Text.EMOJI['suit'][c.suit]

        @staticmethod
        def eng_short_suit(c: Card) -> str:
            # [0] because only first letter is used (short suit)
            return (
                Card.Text.ENG['rank'][c.rank] + '|' + Card.Text.ENG['suit'][c.suit][0]
            )

        @staticmethod
        def classic(c: Card) -> str:
            return Card.Text.CLASSIC['rank'][c.rank] + Card.Text.CLASSIC['suit'][c.suit]

        @staticmethod
        def emoji_shirt(c: Card) -> str:
            return Card.Text.EMOJI['shirt']

        @staticmethod
        def eng_shirt(c: Card) -> str:
            return Card.Text.ENG['shirt']

        @staticmethod
        def classic_shirt(c: Card) -> str:
            return Card.Text.CLASSIC['shirt']

    def __init__(
        self, rank: int | str | Card | None = None, suit: int | str | None = None
    ) -> None:
        self.rank: int | None
        self.suit: int | None
        # in case when all rank and suit described only in rank attribute
        if isinstance(rank, str):
            splited = split(rank)
            if not splited:
                raise EmptyValueError('empty splited')
            if (not suit and len(splited) != 2) or (suit and len(splited) != 1):
                raise ValueError(f'not supported: {rank=} | {suit=}')
            if len(splited) == 2:
                rank, suit = splited

        # convert string-integer into integer:
        if isinstance(rank, str) and rank in [
            str(n) for n in range(len(Card.Text.ENG['rank']))
        ]:
            rank = int(rank)
        if isinstance(suit, str) and suit in [
            str(n) for n in range(len(Card.Text.ENG['suit']))
        ]:
            suit = int(suit)

        # init:
        if isinstance(rank, Card):
            assert not suit, f'not supported: {rank=} | {suit=} together'
            instance = rank
            if isinstance(instance, tuple):
                self.rank, self.suit = instance
            elif isinstance(instance, Card):
                self.rank, self.suit = (instance.rank, instance.suit)
            else:
                raise ValueError(f'not supported {instance=}')
        elif isinstance(rank, str):
            try:
                filtered = next(
                    filter(
                        # lambda text_data: eq_first(rank, text_data),
                        functools.partial(eq_first, rank),
                        Card.Text.ENG['rank'],
                    )
                )
            except StopIteration:
                raise ValueError(f'not supported: {rank=} | {suit=}')
            self.rank = Card.Text.get_rank_value(filtered)
        else:
            self.rank = rank

        if isinstance(suit, str):
            try:
                filtered = next(
                    filter(functools.partial(eq_first, suit), Card.Text.ENG['suit'])
                )
            except StopIteration:
                raise ValueError(f'not supported: {rank=} | {suit=}')
            self.suit = Card.Text.get_suit_value(filtered)
        elif not hasattr(self, 'suit'):
            # hasattr - because we probably set this attribute upper
            self.suit = suit

        if (self.rank is not None and self.suit is None) or (
            self.rank is None and self.suit is not None
        ):
            raise ValueError(
                f'not supported: {rank=} | {suit=}. \n{self.rank = } | {self.suit = }'
            )

    def __getitem__(self, key: str) -> int:
        """
        Card support access to self attributes via card[key].

        >>> Card('Ace|Hearts')['rank']
        14
        """
        return self.__dict__[key]

    def get_str(self, method_name: str = 'classic'):
        """
        Simple shortcut to get card representatin in provided way.
        """
        return self.Text.get_str(self, method_name)

    def get_hiden(self, method_name: str = 'classic_shirt'):
        """
        Simple shortcut to get card in hidden way (card face down).
        """
        return self.Text.get_str(self, method_name)

    def __str__(self) -> str:
        return self.Text.get_str(self)

    def __repr__(self) -> str:
        return self.Text.get_repr(self)

    def __lt__(self, other: object) -> bool:  # self < other
        if not isinstance(other, Card):
            return NotImplemented
        elif not (
            isinstance(self.rank, int)
            and isinstance(self.suit, int)
            and isinstance(other.rank, int)
            and isinstance(other.suit, int)
        ):
            logger.warning(
                'Comparison between not mirrored joker and card is not implemented: '
                f'{self} < {other}'
            )
            return NotImplemented
        else:
            return (
                self.rank < other.rank
                or self.rank == other.rank
                and self.suit < other.suit
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    @property
    def is_joker(self) -> bool:
        return isinstance(self, JokerCard)

    @property
    def is_mirror(self) -> bool:
        raise NotImplementedError(f'Card {self} is not a Joker.')

    def get_mirrored(
        self, reflection: Card, attr: str | None = None, val: int | None = None
    ) -> JokerCard:
        """
        Create and return new JokerCard mirrored from reflection.
        Also set a specific value for refelection attrubite before.

        Parameters
        ----------
        reflection : from which Card make a reflection
        attr : Card attribute 'rank' or 'suit'
        val : new attribute value
        """
        raise NotImplementedError(f'Card {self} is not a Joker.')


class JokerCard(Card):
    """
    Joker is a card that could be a mirror of any Card to achive spicific poker
    combination.

    kind : Joker color `1` (black) or `0` (red)
    """

    class Text(Card.Text):
        EMOJI = {'joker': ['🤡', '😈']}
        CLASSIC = {'joker': ['🤡', '😈']}
        ENG = {'joker': ['red', 'black']}

        @staticmethod
        def get_kind_value(kind: str) -> int:
            try:
                return JokerCard.Text.ENG['joker'].index(kind)
            except ValueError:
                raise ValueError(f'not supported: {kind=}')

        @staticmethod
        def default(c: Card) -> str:
            if not isinstance(c, JokerCard):
                raise TypeError
            return f'JokerCard({c.kind}, reflection={Card.Text.default(c)})'

        @staticmethod
        def classic(c: Card):
            if not isinstance(c, JokerCard):
                raise TypeError
            return JokerCard.Text.CLASSIC['joker'][c.kind] + (
                f'(as {Card.Text.classic(c)})' if c.is_mirror else ''
            )

        @staticmethod
        def emoji(c: Card) -> str:
            if not isinstance(c, JokerCard):
                raise TypeError
            try:
                return JokerCard.Text.EMOJI['joker'][c.kind] + (
                    f'(as {Card.Text.emoji(c)})' if c.is_mirror else ''
                )
            except IndexError:
                return JokerCard.Text.default(c)

        @staticmethod
        def eng_short_suit(c: Card) -> str:
            if not isinstance(c, JokerCard):
                raise TypeError
            try:
                return f'{JokerCard.Text.ENG["joker"][c.kind]}' + (
                    f'({Card.Text.eng_short_suit(c)})' if c.is_mirror else ''
                )
            except IndexError:
                return Card.Text.default(c)

    def __init__(
        self,
        kind: int | str | JokerCard,
        reflection: Card | str | None = None,
        initial: dict[str, int] = {},
    ) -> None:
        if isinstance(kind, str):
            splited = split(kind)
            if not splited:
                raise EmptyValueError('empty splited')
            if len(splited) not in [1, 2, 3]:
                raise ValueError
            kind = splited.pop(0)
            if splited:
                assert not reflection
                reflection = '|'.join(splited)
            if isinstance(kind, str):
                self.kind = JokerCard.Text.get_kind_value(kind)
            else:
                raise ValueError(f'JokerCard defenition goes in wrong way: {kind=}')

        elif isinstance(kind, int):
            self.kind = kind
        elif isinstance(kind, JokerCard):
            self.kind = kind.kind
        else:
            raise TypeError()

        if reflection:
            super().__init__(reflection)
        elif isinstance(kind, JokerCard):
            super().__init__(kind.rank, kind.suit)
        else:
            super().__init__()

        for k in initial:
            self.__dict__[k] = initial[k]

    def __lt__(self, other: object) -> bool:
        if isinstance(other, JokerCard):
            return (
                super().__lt__(other)
                or self.kind < other.kind
                and super().__eq__(other)
            )
        elif isinstance(other, Card):
            return super().__lt__(other)
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JokerCard):
            return NotImplemented
        return super().__eq__(other) and self.kind == other.kind

    @property
    def is_mirror(self) -> bool:
        return not (self.rank is None and self.suit is None)

    def get_mirrored(
        self, reflection: Card, attr: str | None = None, val: int | None = None
    ) -> JokerCard:
        assert isinstance(reflection, Card)
        assert (attr is not None and val is not None) or (attr is None and val is None)
        initial = {attr: val} if isinstance(attr, str) and isinstance(val, int) else {}
        return JokerCard(self, reflection, initial)


class CardList(list[Card]):
    """
    Mutable sequence of Cards. It could be deck, cards in a hand or on the table, etc.

    Could be generated from:
        `*cards`:
    - instances of `Card`/`JokerCard`
    - str: `'king clubs'`, `'Q|h'`, `'black'`, `'red(Jack, C)'`

        `instance`:
    - iterable contained cards (including `CardList`)
    - str: the same as for cards, but seperated by comma (,)

        `new_card_instances` for default is False

        Card values could be:
    - rank: `14` (Ace), `13` (King), ... `3` (Three) or `2` (Two)
    - suit: `4` (Spades), `3` (Hearts), `2` (Diamonds) or `1` (Clubs)

    If no argument is given, the constructor creates a new empty list.
    """

    @staticmethod
    def generator(
        *cards: Card | JokerCard | str,
        new_card_instances: bool = False,
    ):
        """
        Parsing cards strings to CardList.
        """
        for card in cards:
            # type cheking
            if isinstance(card, Iterable) and not isinstance(card, str):
                raise ValueError(
                    f'Invalid card type {type(card)}. Can by {str}{Card}{JokerCard}. ',
                    'Did you forget to unpack(*) list of cards? ',
                    f'{card=} in {cards=}. ',
                )
            if not card:  # blank card init like ''
                continue

            if isinstance(card, Card):
                yield Card(card) if new_card_instances else card
            elif isinstance(card, JokerCard):
                yield JokerCard(card) if new_card_instances else card
            elif isinstance(card, tuple):
                raise NotImplementedError('Tuple definition for card not available. ')
            elif isinstance(card, str):
                assert not new_card_instances, 'not supported for `str` defenition'
                assert (
                    ' ' not in card
                ), 'card contains space symbol, but it reserved for CardList seperator'
                assert (
                    '[' not in card and ']' not in card
                ), 'card contains [] symbols, but it reserved for Stacks seperator'
                try:
                    yield Card(card)
                except ValueError as card_exc:
                    try:
                        yield JokerCard(card)
                    except ValueError as joker_exc:
                        raise ValueError(
                            f'not supported: {card = }\n',
                            *card_exc.args,
                            *joker_exc.args,
                        )
                    except EmptyValueError:
                        continue
                except EmptyValueError:
                    continue
            else:
                raise ValueError(
                    f'Invalid card type: {type(card)}. ', f'{card=} in {cards=}. '
                )

    def __init__(
        self,
        *cards: Card | JokerCard | str,
        instance: Iterable[Card] | str | None = None,
        new_card_instances: bool = False,
    ):
        def brackets_checker(__list: list[str]):
            mapped = map(lambda x: x in ('[', ']', '[]', ']['), __list)
            if any(mapped) and (
                len(__list) > 1
                and (__list[0], __list[-1]) != ('[', ']')
                or len(__list) == 0
                and __list != ('[]',)
                or len(list(filter(None, mapped))) > 2
            ):
                raise ValueError(f'Invalid brackets `[` `]` at {instance=}')
            return True

        if isinstance(instance, str):
            assert (
                not cards
            ), 'Not supported definition for `instance` and `cards` together. '

            # space symbol is a card seperator
            splited = split(instance, by_symbols=' ')

            # check [] brackets
            assert brackets_checker(splited)

            # square bracket [ ] reserved for Stacks seperator
            filtered = filter(lambda x: x not in ('[', ']', '[]'), splited)

            super().__init__(
                self.generator(*filtered, new_card_instances=new_card_instances)
            )
        elif instance is not None:
            assert (
                not cards
            ), 'Not supported definition for `instance` and `cards` together. '
            if new_card_instances:
                super().__init__(self.generator(*instance, new_card_instances=True))
            else:
                super().__init__(instance)
        else:
            super().__init__(
                self.generator(*cards, new_card_instances=new_card_instances)
            )

    def __repr__(self) -> str:
        return super().__repr__()

    def __str__(self) -> str:
        return ' '.join([c.__str__() for c in self])

    @overload
    def __getitem__(self, __i: SupportsIndex, /) -> Card:
        ...

    @overload
    def __getitem__(self, __s: slice, /) -> CardList:
        ...

    def __getitem__(self, __s: SupportsIndex | slice, /) -> CardList | Card:
        return (
            CardList(*super().__getitem__(__s))
            if isinstance(__s, slice)
            else super().__getitem__(__s)
        )

    def insert_left(self, __object: Card) -> None:
        super().insert(0, __object)


    def copy(self, deep: bool = False) -> CardList:
        """
        Return shollow or deep copy of the CardList.
        """
        # [NOTE] we need to redefine copy behaivor to control returned type.
        return CardList(instance=self, new_card_instances=deep)

    @property
    def length(self) -> int:
        return self.__len__()

    @property
    def first(self) -> Card:
        return self[0]

    @property
    def last(self) -> Card:
        return self[-1]

    def shuffle(self) -> CardList:
        """
        Shuffle self list of cards and return self
        """
        random.shuffle(self)
        return self

    def sortby(self, attr: str = 'rank', *, reverse: bool = True) -> CardList:
        """
        Total 'in place' sorting by specific attribute `rank` or `suit`. Using Card
        another attribute and Jokers `kind` as following sorting parameters.

        - `Mirrored` Jokers placed ater theirs reflections.
        - `Unreflected` Jokers placed at the end/front of list.
        - `Black` Joker worth more than `Red` one with other things being equal.

        >>> CardList('2|C', '2|D', 'Ace|H', 'red(Ace|S)').sortby('rank')
        [red(Ace|S), Ace|H, 2|D, 2|C]

        return self
        """
        assert attr in ('rank', 'suit')
        another_attr = 'rank' if attr == 'suit' else 'suit'

        def key(card: Card):
            card_priority = 1000 if SET_JOKERS_AFTER_EQUAL_CARD else -1
            if isinstance(card, JokerCard):
                if card.is_mirror:
                    return (card[attr], card[another_attr], card.kind)
                else:
                    # to put them to the last/first group
                    return (-1, -1, card.kind)
            return (card[attr], card[another_attr], card_priority)

        # [NOTE]
        # by default sort save the original position of cards that equal by
        # attr (aka 'stabel sorting'). But we need 'total' sorting by all
        # attributes one after another.
        super().sort(key=key, reverse=reverse)
        return self

    def isolate_jokers(
        self, *, sort_attr: str, sort_reverse: bool = True
    ) -> tuple[CardList, CardList]:
        """
        Isolate not mirrored jokers into a new list. Self list is sorted(!) inside.

        Return `self`, `jokers`
        """
        self.sortby(sort_attr, reverse=sort_reverse)
        jokers = CardList()
        item = attrgetter('last' if sort_reverse else 'first')
        while self and item(self).is_joker and not item(self).is_mirror:
            jokers.append(self.pop() if sort_reverse else self.pop(0))
        return self, jokers

    def groupby(self, attr: str) -> Generator[tuple[bool, CardList], None, None]:
        """
        Yield CardList (a group) of equal ranks/suits in a row from highest to smallest.

        attr: `rank` or `suit`.

        [NOTE]
        Last group contains NOT mirrored Jokers if they appeare. Morrored Jokers
        processed like other Cards. Self list of cards is sorted(!) inside.

        Example
        -------

        by `rank`
        - Yeild [Black, Red]
        - Yield [Ace Hearts, Ace Diamond] -- first group
        - Yield [Quen Qlubs, Quen Spades, Quen Diamond] -- second group
        - Yield [10 Spades] -- third group
        - Yield [3 Qlubs] -- forth group
        - Yield [Black as 2 Hearts, Red as 2 Spades]

        by `suit`
        - Yield [Ace Hearts] -- first group
        - Yield [Quen Spades, 10 Spades] -- second group
        - Yield [Quen Diamond] -- third group
        - Yield [Quen Qlubs, 3 Qlubs] -- forth group
        """
        self.sortby(attr)

        for key, group in itertools.groupby(self, key=attrgetter(attr)):
            yield bool(key is None), CardList(instance=group)


Stacks: TypeAlias = list[CardList]


class Decks:
    """
    Class for decks generators used to filled up game deck before every round begins.
    """

    @staticmethod
    def full_deck_plus_jokers(config: DeckConfig):
        min, max = config.interval.borders
        for _ in range(config.iterations_amount):
            for rank in reversed(range_inclusevly(min.rank, max.rank)):
                for suit in reversed(range_inclusevly(min.suit, max.suit)):
                    yield Card(rank, suit)

            for i in range(config.jokers_amount):
                yield JokerCard('red') if i % 2 else JokerCard('black')

    @staticmethod
    def factory_from(table: CardList, hands: Stacks):
        """
        Collect deck from provided values deck with will guarantee the same table and
        hands after deals and flop stages. Make shure that shuffling(!) is off.

        Mostly for test porpuses.
        """
        deck = CardList()
        deck.extend(table)
        for cards in zip(*reversed(hands), strict=True):
            deck.extend(cards)
        return deck
