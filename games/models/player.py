from __future__ import annotations

import itertools
import logging


from typing import Any, Callable, Iterable, Iterator, Optional, Reversible, TypeVar
from django.db.models import F
from core.functools.looptools import circle_after, looptools
from core.functools.utils import StrColors, init_logger, isinstance_items
from core.models import CreatedModifiedModel
from django.db import IntegrityError, models
from django.db.models import manager
from django.db.models.query import QuerySet
from django.urls import reverse
from games.backends.cards import CardList, Decks, Stacks
from games.backends.combos import ComboKind, ComboStacks
from games.models import Game
from games.models.fields import CardListField, StacksField
from users.models import User
from django.db.models.fields import Field
from django.core.exceptions import ValidationError
from ..services import configurations
from core.types import JSON
from django.db.models import manager, functions


logger = init_logger(__name__, logging.INFO)


_T = TypeVar('_T')


class PlayerQuerySet(models.QuerySet):
    # define custom methods here
    def annotate_bet_total_with_none(self):
        return self.active.annotate(bet_total_none=models.Sum('bets__value'))

    @property
    def active(self):
        """Players that have not said `pass`."""
        return self.filter(is_active=True)



class IterableManager(models.Manager[_T]):
    def __iter__(self) -> Iterator[_T]:
        return iter(self.all())

    def __getitem__(self, index: int):
        return self.all()[index]


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
        qs = qs.annotate(
            bet_total=functions.Coalesce(models.Sum('bets__value'), 0)
        )
        return qs


    def aggregate_max_bet(self) -> int:
        return self.aggregate(max=models.Max('bet_total'))['max']

    def aggregate_sum_all_bets(self) -> int:
        return self.game.players.aggregate(models.Sum('bet_total'))

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
        qs = self.active.annotate(bet_total_none=models.Sum('bets__value'))
        return qs.order_by('bet_total_none', 'is_dealer')

    def annotate_bet_total_with_none(self):
        return self.active.annotate(bet_total_none=models.Sum('bets__value'))


    @property
    def without_bet(self):
        """for active players starting after dealer"""
        return self.after_dealer.annotate_bet_total_with_none().filter(is_active=True, bet_total_none=None)

    def check_bet_equality(self):
        """True if all beds equal (for active players)."""
        max_ = self.active.aggregate(models.Max('bet_total'))
        min_ = self.active.aggregate(models.Min('bet_total'))
        agregated = self.active.aggregate(
            diff=models.Max('bet_total') - models.Min('bet_total')
        )
        # if agregated['diff'] is None:
        #     m = 'Checking bet equality at game that has no bets at all. Return true.'
        #     logger.warning(m)
        #     return True
        # if self.without_bet.exists():
        #     m = (
        #         'Checking bet equality at game where not every player has placed a '
        #         'bet. Return False.'
        #     )
        #     logger.warning(m)
        #     return False
        return agregated['diff'] == 0

    @property
    def after_dealer(self):
        """All active players starting after dealer button."""
        return self.order_by('is_dealer', 'position').filter(is_active=True)

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

    # @property
    # def no_bet(self):
    #     return self.filter(is_active=True, bet_total=None)


class Player(CreatedModifiedModel):
    """Model for representing single user at curtain game.

    `is_dealer`
    A dealer button is used to represent the player in the dealer position.
    The dealer button rotates clockwise after each round, changing the position of the
    dealer and blinds. Dealer position number is always 0.

    """

    # frist manager defined at model is default, therefore it`s used for related fields
    # also it used by internal django`s processings
    _manager_for_related_fields: PlayerManager[Player] = PlayerManager()
    # classic manager for getting access to all player model
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
    is_dealer: bool  # annotated by PlayerQuerySet
    is_host: bool = models.BooleanField('game host', default=False)
    is_active: bool = models.BooleanField('player did not say "pass" yet', default=True)

    @property
    def other_players(self) -> QuerySet[Player]:
        return self.game.players.filter(~models.Q(pk=self.pk))

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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

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

    def clean(self) -> None:
        # check and clean one player instance
        # if not hasattr(self, 'bet'):
        #     PlayerBet.objects.create(player=self)

        # check all player dependences at this player Game
        game = self.game

        # check host
        try:
            game.players.host
        except Player.DoesNotExist as e:
            raise IntegrityError(f'{game} has no host: {e}')
        except Player.MultipleObjectsReturned as e:
            raise IntegrityError(f'Many hosts at {game}: {e}')

        # chek dealer
        try:
            game.players.dealer
        except Player.DoesNotExist as e:
            raise IntegrityError(f'{game} has no dealer: {e}')
        except Player.MultipleObjectsReturned as e:
            raise IntegrityError(f'Many dealers at {game}: {e}')

        # ckeck players positions
        positions = [p.position for p in game.players]
        if list(range(game.players.count())) != positions:
            raise IntegrityError(f'{game} has invalid players positions: {positions}')


def get_bet_default():
    return []


def type_is_list_int(values: list[int]):
    if not isinstance(values, list) or not isinstance_items(values, list, int):
        raise ValidationError(
            f'Type error for bet values. Get: {type(values)}. Expected: list[int]. '
        )


def bet_multiplicity(value: int):
    devider = configurations.DEFAULT.bet_multiplicity
    if value % devider:
        raise ValidationError(
            f'Value error: {value}. It is not multiples of small blind. '
        )


class PlayerBetQuerySet(models.QuerySet):
    # define custom methods here
    pass


class PlayerBetManager(IterableManager[_T]):
    def get_queryset(self):
        qs = PlayerBetQuerySet(model=self.model, using=self._db, hints=self._hints)
        return qs

    def was_placed(self):
        return self.exists()

    # def append(self, value):
    #     self.create(value=value)

    @property
    def total(self) -> int:
        """Sum of all bets.

        The same as `player.bet_total` annotated at every player instance by
        `PlayerQuerySet`.
        """
        return self.aggregate(total=models.Sum('value'))['total'] or 0

    def __str__(self) -> str:
        s = ' '.join(str(b) for b in self.all())
        return f'{s}'

    # def sum(self) -> int:
    #     return sum([b.value for b in self.all()])

    # def accept(self) -> int:
    #     """take away player`s beds"""
    #     beds_sum = self.sum()
    #     self.all().delete()
    #     return beds_sum


class PlayerBet(CreatedModifiedModel):
    """Current players bet. After beds applyed it becomes 0."""

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


########################################################################################


########################################################################################


class PlayerCombo(models.Model):
    player: Player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='_combo'
    )

    # combo kind name
    name: str = models.CharField(max_length=20, default='<not tracked yet>')
    priority: float = models.FloatField(blank=True, null=True)

    # combo stacks cases
    rank = StacksField()
    suit = StacksField()
    row = StacksField()
    highest_card = StacksField()

    def __init__(self, *args, player: Player = None) -> None:
        kwargs: dict[str, Any] = {}
        kwargs.setdefault('player', player) if player else ...
        super().__init__(*args, **kwargs)

    def __getitem__(self, key: str) -> Stacks:
        if key in ComboKind.CONDITION_KEYS:
            if hasattr(self, key):
                return getattr(self, key)
            raise RuntimeError
        raise KeyError

    def setup(self):
        # if self.name is not '<not tracked yet>':
        #     print("raise Warning('calling setup for already initialized combo')")
        stacks = ComboStacks()
        kind = stacks.track_and_merge(self.player.hand, self.player.game.table)

        if kind is None:
            self.name = '<no combination found>'
            self.save
        else:
            self.priority = kind.priority
            self.name = kind.name

            self.rank = stacks.cases.get('rank', [])
            self.suit = stacks.cases.get('suit', [])
            self.row = stacks.cases.get('row', [])
            self.highest_card = stacks.cases.get('highest_card', [])

            self.save()

    def __str__(self) -> str:
        return (
            self.name
            + ': '
            + (str(self.rank) if self.rank else '')
            + (str(self.suit) if self.rank else '')
            + (str(self.row) if self.rank else '')
            + (str(self.highest_card) if self.rank else '')
        )
