"""Tools for handling poker combinations.

developing:
[ ] get_condition -- refactoring
[ ] track row -- refactoring
[ ] ComboStacks.__init__(...)
[ ] doc string

"""

from __future__ import annotations
from dataclasses import dataclass
import functools

import itertools
from copy import deepcopy
import logging
from operator import attrgetter
from typing import TYPE_CHECKING, ClassVar, Iterable

from core.functools.looptools import looptools
from core.functools.utils import StrColors, init_logger
from core.functools.utils import is_sorted
from games.services.cards import Card, CardList, JokerCard, Stacks
from games.services import combo_trackers

if TYPE_CHECKING:
    from games.models.player import Player

logger = init_logger(__name__, logging.WARNING)

Conditions = dict[str, tuple[int, ...]]


class ExtraComboException(Exception):
    def __init__(self, cases: Conditions, nearest: ComboKind) -> None:
        self.cases = cases
        self.nearest = nearest
        return super().__init__(
            f'Combo {cases} has more opportunity than described in reference list. '
            f'Redefine list of possible combos where all keyses will be considered. '
        )


class NoComboException(Exception):
    def __init__(self, cases: Conditions, nearest: ComboKind) -> None:
        assert nearest.name == 'high card'

        self.cases = cases
        self.nearest = nearest
        return super().__init__(
            f'No reference combination found for {cases}. '
            f'At least {self.nearest} combination should be sytisfied. '
        )


@functools.total_ordering
class ComboKind:
    """Class for annotation specific type of combination.

    All groups lists shold be init by straight sequences from highest to smallest.
    Anyway, they have sorted inside, to be shure.

        `name`: Verbose name of combination kind
        `cases`: Main dictianary to store all conditional cases
    """

    _CONDITION_KEYS: ClassVar[set[str]] = {'rank', 'suit', 'row', 'highest_card'}

    def __init__(self, *, name: str = '', priority: float | None = None, **cases):
        self.name = name
        self.priority = priority

        assert self._CONDITION_KEYS.issuperset(cases), f'Invalid keys: {cases}. '
        self.cases: Conditions = {
            k: tuple(sorted(v, reverse=True)) for k, v in cases.items()
        }

    def __repr__(self) -> str:
        return f'`{self.name}`'

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, ComboKind):
            return NotImplemented
        return self.priority == __o.priority

    def __lt__(self, __o: object) -> bool:  # self < other
        if not isinstance(__o, ComboKind):
            return NotImplemented
        if self.priority is None or __o.priority is None:
            logger.error('Comparison between combos without priority. ')
            return NotImplemented
        return self.priority < __o.priority

    def is_minor_combo_for(self, major: Conditions):
        """
        Return whether self (minor) combination cases includes (or equal) major cases.
        self cases <= major

        >>> self = ComboKind(suit=[5], row=[5])
        >>> self.is_minor_combo_for({'suit': [6], 'row': [7]})
        True
        >>> self = ComboKind(row=[5])
        >>> self.is_minor_combo_for({'row': [4, 3]})
        False
        """
        assert is_sorted(
            *self.cases.values(), reverse=True
        ), f'Some condition is not row sequence in {self}'
        assert is_sorted(
            *major.values(), reverse=True
        ), f'Some condition is not row sequence in {major}'

        if not major.keys() >= self.cases.keys():
            return False

        value: bool = True
        for key in self.cases:
            # длина больше или равна
            value = value and len(major[key]) >= len(self.cases[key])
            for greater, smaller in zip(major[key], self.cases[key]):
                # каждый элемент больше или равен
                value = value and greater >= smaller
                if not value:
                    break

        return value


class ComboKindList(list[ComboKind]):
    def __init__(self, __iterable: Iterable[ComboKind], *, set_pryority=True) -> None:
        super().__init__(__iterable)
        if set_pryority:
            assert self
            priority: float = 0.00
            step: float = 1.00 / len(self)
            for combo in self:
                combo.priority = round(priority, 2)
                priority += step

    def get(self, name: str) -> ComboKind:
        try:
            return next(filter(lambda c: c.name == name, self))
        except StopIteration:
            raise ValueError(
                f'ComboKindList do not contains combos with `{name}` name. '
                f'Awailable: {self}'
            )

    def get_by_conditions(self, conditions: Conditions) -> ComboKind:
        """Finding equivalent combination in self list.

        Going through all combos from highest to smallest until self combination is not
        major for referense.
        """
        for ref in reversed(self):
            if conditions == ref.cases:
                return ref
            if ref.is_minor_combo_for(conditions):
                raise ExtraComboException(cases=conditions, nearest=ref)
        raise NoComboException(cases=conditions, nearest=ref)


CLASSIC_COMBOS = ComboKindList(
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


@functools.total_ordering
class ComboStacks:
    """Contains lists of stacks equivalented to ComboKind condtitions groups.
    By default `init()` creates an epty object.
    Call `track_and_merge()` method to complete initialization.
    """

    source: CardList
    leftovers: CardList
    cases: dict[str, Stacks]
    extra_cases: dict[str, Stacks]

    @property
    def conditions(self):
        conditions: Conditions = {}
        for key in self.cases:
            conditions[key] = tuple(cards.length for cards in self.cases[key])
        return conditions

    @property
    def cases_chain(self):
        return itertools.chain(*itertools.chain(*self.cases.values()))

    # default track methods
    track_equal = combo_trackers.track_equal
    track_row = combo_trackers.track_row
    track_highest = combo_trackers.track_highest

    def __init__(self, player: Player | None = None):
        if player:
            pass
        self.cases = {}
        self.extra_cases = {}

    def __repr__(self) -> str:
        return f'ComboStacks{str(list(self.cases_chain))}'

    def __str__(self) -> str:
        return self.__repr__()

    def __bool__(self) -> bool:
        return any(any(bool(cl) for cl in stacks) for stacks in self.cases.values())

    def __comparison_permition(self, other: ComboStacks):
        if self.conditions != other.conditions:
            logger.error('Comparison between combos stacks with different conditions. ')
            return False
        if not len(self.leftovers) == len(other.leftovers):
            logger.error('Comparison between combos whith different len of source. ')
            return False
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ComboStacks) or not self.__comparison_permition(other):
            return NotImplemented

        # we won`t use self.source attribute, because it contains not processed at
        # tracking jokers (they are not mirrored), therefore two seperate checkings
        # for cases and for leftovers
        return self.cases == other.cases and self.leftovers == other.leftovers

    def __lt__(self, other: object) -> bool:  # self < other
        if not isinstance(other, ComboStacks) or not self.__comparison_permition(other):
            return NotImplemented

        # we won`t use self.source attribute, because it contains not processed at
        # tracking jokers (they are not mirrored). [1] comare cases # [2] compare other
        for key in self.cases:
            if not self.cases[key] < other.cases[key]:
                return False
        if not self.leftovers < other.leftovers:
            return False

        return True

    def track(self, possible_highest: Card = Card(14, 4)) -> None:
        self.track_equal(possible_highest, 'suit')
        self.track_equal(possible_highest, 'rank')
        self.track_row(possible_highest)

    def merge(self, references: ComboKindList) -> ComboKind:
        try:
            return references.get_by_conditions(self.conditions)
        except ExtraComboException as e:
            logger.info(f'Exeption was catched: {e}')
            logger.info(
                'Solution is: '
                '(1) Copied extra conditionas and staks in self.extra for any uses. '
                f'(2) Merjed self into nearest {e.nearest}. '
            )

            self.extra_cases = deepcopy(self.cases)
            self.trim_to(e.nearest)
            return e.nearest

    def trim_to(self, reference: ComboKind) -> None:
        assert self.cases
        assert is_sorted(*self.cases.values(), key=lambda s: len(s), reverse=True)

        # cut off excess condtitions 'rank' 'suit' 'row':
        for unused_key in self.cases.keys() - reference.cases.keys():
            del self.cases[unused_key]

        # reduce extra cards in useable conditions
        for key in reference.cases:
            del self.cases[key][len(reference.cases[key]) :]
            for amount, cards in zip(
                reference.cases[key], self.cases[key], strict=True
            ):
                del cards[amount:]

    def track_and_merge(
        self,
        *stacks: CardList,
        references=CLASSIC_COMBOS,
        possible_highest: Card = Card(14, 4),
    ) -> ComboKind:
        """Find any possible combination in stacks (even a Highest Card).

        `*stacks`: where to trace combinations
        `possible_highest`: the most highest card in the deck
        (to prepend jokers into straight combos from the edges)

        return: reference of ComboKind which self has merged to

        To coplite searching metodh creates a new merged CardList inside.
        Source stacks remain unmodified.
        """
        self.source = CardList(instance=itertools.chain(*stacks))
        if not self.source:
            logger.warning('no cards for tracking was provided')

        self.track(possible_highest=possible_highest)
        try:
            kind = self.merge(references)
        except NoComboException as e:
            logger.info(
                f'Exeption was catched: {e}. '
                'Solution is: added `highest_card` case with one card'
            )
            self.track_highest(possible_highest)
            self.extra_cases = deepcopy(self.cases)
            self.trim_to(e.nearest)
            kind = e.nearest

        # Note: we check `not c.is_jokers` because jokers are always has been used.
        # if we skip this cheking, not mirrored jokers at source will compare with
        # mirrored at stacks and it return false.
        used = list(self.cases_chain)
        filtered = filter(lambda c: not c.is_joker and c not in used, self.source)
        self.leftovers = CardList(instance=filtered)

        return kind


@dataclass(order=True)
class Combo:
    kind: ComboKind
    stacks: ComboStacks


if __name__ == '__main__':
    pass
