from __future__ import annotations

import logging
from typing import TypeVar

from core.functools.utils import StrColors, init_logger
from core.models import (
    CreatedModifiedModel,
    FullCleanSavingMixin,
    UpdateMethodMixin,
    IterableManager,
)
from core.validators import bet_multiplicity
from django.db import IntegrityError, models
from django.db.models import F, functions
from django.db.models.query import QuerySet
from games.services.cards import CardList
from games.services.combos import Combo, ComboStacks
from games.models import Game
from games.models.fields import CardListField
from users.models import User
from core.functools.looptools import circle_after

logger = init_logger(__name__, logging.INFO)

_T = TypeVar('_T')


class PlayerQuerySet(models.QuerySet):
    pass


class PlayerManager(IterableManager[_T]):
    def get_queryset(self):
        qs = PlayerQuerySet(model=self.model, using=self._db, hints=self._hints)
        # dealer attribute
        qs = qs.annotate(
            is_dealer=models.Case(
                models.When(position=0, then=models.Value(True)),
                models.When(position__gt=0, then=models.Value(False)),
            )
        )
        # bet_total attribute
        qs = qs.annotate(bet_total=functions.Coalesce(models.Sum('bets__value'), 0))
        return qs

    def aggregate_max_bet(self) -> int:
        return self.aggregate(max=models.Max('bet_total'))['max']

    def aggregate_sum_all_bets(self) -> int:
        return self.game.players.aggregate(models.Sum('bet_total'))

    def check_bet_equality(self):
        """True if all beds equal (for active players)."""
        agregated = self.active.aggregate(
            diff=models.Max('bet_total') - models.Min('bet_total')
        )
        return agregated['diff'] == 0

    @property
    def with_max_bet(self) -> Player:
        return self.order_by('-bet_total').first()

    @property
    def order_by_bet(self):
        """Order active players with None bet first then 0 then ascending.
        Starting after dealer."""
        # we need that special annotation to differentiate two types of player bet:
        # [1] player who say check (bets sum = 0)
        # [2] player who has not placed bet yet (bets sum = None)
        # at default annotation when bet_total is None it value replaced by default=0
        qs = PlayerManager._annotate_bet_total_with_none(self.active)
        return qs.order_by('bet_total_none', 'is_dealer')

    @staticmethod
    def _annotate_bet_total_with_none(qs: PlayerQuerySet):
        return qs.annotate(bet_total_none=models.Sum('bets__value'))

    @property
    def without_bet(self):
        """for active players starting after dealer"""
        return self.after_dealer.filter(is_active=True, bets__isnull=True)

    @property
    def after_dealer(self):
        """active players starting after dealer button."""
        return self.order_by('is_dealer', 'position').filter(is_active=True)

    @property
    def after_dealer_all(self):
        """All players (active and passive) starting after dealer button."""
        return self.order_by('is_dealer', 'position')

    @property
    def active(self):
        """Players that have not said `pass`."""
        return self.filter(is_active=True)

    @property
    def host(self):
        return self.get(is_host=True)

    @property
    def dealer(self):
        return self.get(is_dealer=True)


class Player(UpdateMethodMixin, FullCleanSavingMixin, CreatedModifiedModel):
    """Model for representing single user at curtain game.

    `is_dealer`
    A dealer button is used to represent the player in the dealer position.
    The dealer button rotates clockwise after each round, changing the position of the
    dealer and blinds. Dealer position number is always 0.

    """

    _manager_for_related_fields: PlayerManager[Player] = PlayerManager()
    objects: models.Manager[Player] = models.Manager()

    user: User = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='players',
    )
    game: Game = models.ForeignKey(
        to=Game, on_delete=models.CASCADE, related_name='players'
    )
    hand: CardList = CardListField('cards in players hand', blank=True)
    bets: PlayerBetManager[PlayerBet]
    bet_total: int  # annotated by PlayerQuerySet
    position: int = models.PositiveSmallIntegerField(
        'player`s number in a circle starting from 0',
    )
    is_host: bool = models.BooleanField('game host')
    is_dealer: bool  # annotated by PlayerQuerySet
    is_active: bool = models.BooleanField('player did not say "pass" yet', default=True)

    @property
    def other_players(self) -> QuerySet[Player]:
        return self.game.players.filter(~models.Q(pk=self.pk))

    @property
    def combo(self):
        if not self.hand and not self.table:
            return None

        stacks = ComboStacks()
        kind = stacks.track_and_merge(self.hand, self.game.table)
        return Combo(kind, stacks)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'user in game (player)'
        verbose_name_plural = 'users in games (players)'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique: User can play in Game only by one Player',
            ),
        ]
        # nulls_last -- not accessing affect to Zero valus... but None values
        ordering = [F('position').asc(nulls_last=True), 'id']

        # ???
        # base_manager_name = '_manager_for_related_fields'
        # default_manager_name = '_manager_for_related_fields'

    def __repr__(self) -> str:
        try:
            n = self.position if self.position is not None else '?'
            h = '(h)' if self.is_host else ''
            d = '(d)' if self.is_dealer else ''
            return StrColors.underline(f'({n}) {self.user.username}{h}{d}')
        except Exception:
            return f'{self.__class__.__name__} ({self.pk})'

    def __str__(self) -> str:
        return StrColors.underline(self.__repr__())

    def init_clean(self):
        if self.is_host is None:
            # if no other players, this player become a host
            self.is_host = not self.game.players

        if self.position is None:
            last = self.game.players.last()
            self.position = last.position + 1 if last else 0

    def clean(self) -> None:
        "Check constraints and clean values if could, otherwise raising IntegrityError."
        # validate only this player instance
        ...

        # validate all player dependences at this player Game with this player instance
        # replace game player list with self instence and operate with new list
        game = self.game
        players = list(game.players)
        index = players.index(self)
        players[index] = self

        # check host
        amount = len(list(filter(lambda p: p.is_host, players)))
        if not amount:
            raise IntegrityError(f'{game} has no host. ')
        if amount > 1:
            raise IntegrityError(f'Many hosts at {game}. ')

        # chek dealer
        # checking dealer has no sense, because it not an attribute, but jast a rule,
        # that player at 0 position is dealer

        # ckeck players ordering by positions
        # start from position = 0 (from dealer)
        after_dealer = circle_after(lambda p: not p.position, players)
        positions = [p.position for p in after_dealer]
        if list(range(len(players))) != positions:
            raise IntegrityError(f'{game} has invalid players positions: {positions}')


########################################################################################

# def type_is_list_int(*args, **kwargs):
#     raise NotImplementedError


class PlayerBetQuerySet(models.QuerySet):
    pass


class PlayerBetManager(IterableManager[_T]):
    def get_queryset(self):
        qs = PlayerBetQuerySet(model=self.model, using=self._db, hints=self._hints)
        return qs

    def was_placed(self):
        return self.exists()

    @property
    def total(self) -> int:
        """Sum of all bets.

        The same as `player.bet_total` annotated at every player instance by
        `PlayerQuerySet`.
        """
        return self.aggregate(total=models.Sum('value'))['total'] or 0

    def __str__(self) -> str:
        return ' '.join(str(b) for b in self.all())


class PlayerBet(FullCleanSavingMixin, CreatedModifiedModel):
    """Single player bet.

    When game accepted all players bets they all will be deleted.
    To find out total current player bet could be used:
        `total` property at bet manager
        `bets_total` annotation field at player manager
    """

    _manager_for_related_fields: PlayerBetManager[PlayerBet] = PlayerBetManager()
    objects: models.Manager[PlayerBet] = models.Manager()

    player: Player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name='bets'
    )
    value: int = models.PositiveIntegerField(
        validators=[bet_multiplicity],
    )

    def __str__(self) -> str:
        return f'${self.value}'

    def clean(self) -> None:
        pass
