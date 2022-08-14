from __future__ import annotations

import itertools
import logging

from typing import Any, Callable, Iterable, Reversible
from django.db.models import F
from core.functools.looptools import circle_after, looptools
from core.functools.utils import init_logger
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

logger = init_logger(__name__, logging.INFO)


class Player(CreatedModifiedModel):
    """Model for representing single user at curtain game."""

    user: User = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='_players',
    )
    game: Game = models.ForeignKey(
        to=Game, on_delete=models.CASCADE, related_name='_players'
    )
    hand: CardList = CardListField('cards in players hand', blank=True)
    dealer: bool = models.BooleanField('dealer botton', default=False)
    """A dealer button is used to represent the player in the dealer position.
    The dealer button rotates clockwise after each round, changing the position of the
    dealer and blinds.
    """
    position: int = models.PositiveSmallIntegerField(
        'player`s number in a circle starting from 0',
        blank=True,
        null=True,
        default=None,
    )
    host: bool = models.BooleanField('game host', default=False)
    passed: bool = models.BooleanField('player said "pass"', default=False)

    # typing annotation for releted objects (handle it like combo: PlayerCombo)
    @property
    def bet(self) -> PlayerBet:
        if hasattr(self, '_bet'):
            return self._bet
        return PlayerBet.objects.create(player=self)

    @property
    def combo(self) -> PlayerCombo:
        if hasattr(self, '_combo'):
            return self._combo
        return PlayerCombo.objects.create(player=self)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'user in game (player)'
        verbose_name_plural = 'users in games (players)'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique: User can play in Game only by one Player',
            ),
        ]
        ordering = [F('position').asc(nulls_last=True), 'id']

    def __str__(self) -> str:
        p = self.position if self.position is not None else '?'
        h = '(h)' if self.host else ''
        d = '(d)' if self.dealer else ''
        return f'({p}) {self.user.username}{h}{d}'

    # def save(self, *args, **kwargs):



    #         #
    #         #     if self == player:
    #         #         continue
    #         #     if player.position is None:
    #         #         break
    #         # else:
    #         #     self.position = i




    #     super().save(*args, **kwargs)

    def set_dealer(self, value: bool):
        self.dealer = value
        self.save()


class PlayerBet(CreatedModifiedModel):
    """Current players bet. After beds applyed it becomes 0."""

    player: Player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='_bet'
    )
    # maker: bool = models.BooleanField('making a bet now', default=False)
    # """True if game is wating till this player append a bet."""
    value: int = models.PositiveIntegerField(blank=True, null=True, default=None)

    class Meta(CreatedModifiedModel.Meta):
        pass

    def accept(self):
        """take away player`s bet to game`s bank"""
        self.player.game.bank += self.value
        self.player.game.save()
        self.value = 0
        self.save()
        return self.value


    def place(self, value: int):
        """make bet. appending a bet to the game. `user bank -= value` `bet += value`"""
        self.player.user.profile.bank -= value
        self.player.user.profile.save()

        if self.value is None:  # if there were no beds before
            self.value = value
        else:
            self.value += value
        self.save()


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
