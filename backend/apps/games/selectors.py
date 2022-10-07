from __future__ import annotations

from operator import attrgetter
from typing import TYPE_CHECKING, Iterator, Sequence

from core.functools.looptools import circle_after
from core.functools.utils import init_logger, reverse_attrgetter
from django.db import models
from users.models import User

logger = init_logger(__name__)

if TYPE_CHECKING:
    from games.models import Player


class PlayerSelector:
    def __init__(self, source: Sequence[Player]) -> None:
        self._source = source

    def __iter__(self) -> Iterator[Player]:
        return iter(self._source)

    def __getitem__(self, index: int | slice):
        return self._source[index]

    def __bool__(self):
        return bool(self._source)

    def __repr__(self) -> str:
        return f'PlayerSelector{str(self._source)}'

    def __str__(self) -> str:
        return str(self._source)

    def __len__(self) -> int:
        return self._source.__len__()

    @property
    def _list(self):
        """tool for debuging"""
        return list(self)

    # ############################################ players searshing:

    def get(self, *, user: User) -> Player:
        return next(filter(lambda p: p.user == user, self._source))

    def exclude(self, *, player: Player | None = None, user: User | None = None) -> list[Player]:
        if player and user:
            raise ValueError('Too many exclude parameters. ')

        if player:
            return list(filter(lambda p: p != player, self._source))
        elif user:
            user_player = self.get(user=user)
            return list(filter(lambda p: p != user_player, self._source))

        raise ValueError('No exclude parameters was provided. ')


    # ############################################ players updating:

    def reorder_source(self):
        self._source = sorted(self._source, key=attrgetter('position'))

    # ############################################ player's bet:

    def aggregate_min_bet(self) -> int:
        return min(self.active, key=attrgetter('bet_total')).bet_total

    def aggregate_max_bet(self) -> int:
        return max(self.active, key=attrgetter('bet_total')).bet_total
        return self._manager.aggregate(max=models.Max('bet_total'))['max']

    def aggregate_sum_all_bets(self) -> int:
        """for active and passed(!) players"""
        return sum(p.bet_total for p in self._source)

    def aggregate_min_users_bank(self) -> int:
        """for active players"""
        return min(p.user.profile.bank for p in self.active)

    def aggregate_possible_max_bet(self) -> int:
        """for active players.

        To find out pissoble max bet for player we are loking for minimal bank of all
        players with sum of his bet already playced.
        """
        return min(p.user.profile.bank + p.bet_total for p in self.active)

    def check_bet_equality(self) -> bool:
        """True if all beds equal (for active players)."""
        a = self.aggregate_max_bet()
        b = self.aggregate_min_bet()
        return self.aggregate_max_bet() - self.aggregate_min_bet() == 0

    # @property
    # def order_by_bet(self):
    #     # RECODE THIS WITH circle_after -- нам по сути не нужна здесь сортировка...

    #     """Yield ordered active players with None bet first then 0 then ascending.
    #     Starting after dealer.
    #     """
    #     # we need that special annotation to differentiate two types of player bet:
    #     # [1] player who say check (bets sum = 0)
    #     # [2] player who has not placed bet yet (bets sum = None)
    #     # at default annotation when bet_total is None it value replaced by default=0
    #     key = lambda p: (p.bets.exists(), p.bet_total)
    #     for player in sorted(self.after_dealer, key=key):
    #         yield player

    @property
    def next_betmaker(self):
        """
        First active player after player who just has place his bet.
        If all players have placed their bets and they are equal - StopIteration raised.
        """
        try:
            key = lambda p: not p.bets
            return next(circle_after(key, self.after_dealer, raises=True))
        except ValueError:
            chellenging_bet = self.aggregate_max_bet()
            key = lambda p: p.bet_total < chellenging_bet
            return next(circle_after(key, self.after_dealer, raises=True))

    @property
    def without_bet(self):
        """for active players starting after dealer"""
        key = lambda p: not p.bets and p.is_active
        return filter(key, self.after_dealer)

    @property
    def with_max_bet(self) -> Player:
        return max(self._source, key=attrgetter('bet_total'))

    # ############################################ base filtering:

    @property
    def after_dealer(self) -> Iterator[Player]:
        """active players starting after dealer button."""
        key = attrgetter('is_dealer')
        exclude = lambda p: not p.is_active
        return circle_after(key, self._source, inclusive=False, exclude=exclude)

    @property
    def after_dealer_all(self) -> Iterator[Player]:
        """All players (active and passive) starting after dealer button."""
        return circle_after(attrgetter('is_dealer'), self._source, inclusive=False)

    @property
    def active(self) -> Iterator[Player]:
        """Players that have not said `pass`."""
        return filter(attrgetter('is_active'), self._source)

    @property
    def passed(self) -> Iterator[Player]:
        """Players that have said `pass`."""
        return filter(reverse_attrgetter('is_active'), self._source)

    @property
    def host(self) -> Player:
        return next(filter(attrgetter('is_host'), self._source))

    @property
    def dealer(self) -> Player:
        return next(filter(attrgetter('is_dealer'), self._source))
