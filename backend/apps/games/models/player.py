from __future__ import annotations

from core.models import CreatedModifiedModel, FullCleanSavingMixin, get_list_default
from core.utils import init_logger
from core.validators import int_list_validator
from django.db import models
from django.db.models import F
from games.models import Game
from games.models.fields import CardListField
from games.models.managers import PlayerManager
from games.services.cards import CardList
from games.services.combos import Combo, ComboStacks
from users.models import User

logger = init_logger(__name__)


class Player(FullCleanSavingMixin, CreatedModifiedModel):
    """
    Model for representing single user at curtain game.
    """

    _manager_for_related_fields: PlayerManager[Player] = PlayerManager()
    objects: PlayerManager[Player] = PlayerManager()

    user: User = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='players',
    )
    game: Game = models.ForeignKey(
        to=Game,
        on_delete=models.CASCADE,
        related_name='players_manager',
    )
    hand: CardList = CardListField(blank=True)

    # [NOTE]
    # for PlaceBetCheck action we append 0 to bets, it makes us to know: have user
    # made an answer or not. So bets = [0] means that bet was placed, but with 0 value.
    bets: list[int] = models.JSONField(
        blank=True,
        default=get_list_default,
        validators=[int_list_validator],
    )
    position: int = models.PositiveSmallIntegerField()
    is_host: bool = models.BooleanField()
    is_active: bool = models.BooleanField('not passed player', default=True)

    @property
    def bet_total(self):
        return sum(self.bets)

    @property
    def is_dealer(self):
        """
        A dealer button is used to represent the player in the dealer position.
        The dealer button rotates clockwise after each round, changing the position of
        the dealer and blinds. Dealer position number is always 0.
        """
        return self.position == 0

    @property
    def is_performer(self):
        return self == self.game.stage.performer

    @property
    def other_players(self):
        return self.game.players.exclude(player=self)

    @property
    def combo(self):
        if not self.hand and not self.game.table:
            return None

        stacks = ComboStacks()
        kind = stacks.track_and_merge(
            self.hand,
            self.game.table,
            references=self.game.config.combos,
            possible_highest=self.game.config.deck.interval.max,
        )
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
        # nulls_last -- not makes affect to 0 (zero) values, but None values
        ordering = [F('position').asc(nulls_last=True), 'id']

    def __repr__(self) -> str:
        n = self.position if self.position is not None else '?'
        h = '(h)' if self.is_host else ''
        d = '(d)' if self.is_dealer else ''
        name = self.user.username
        return f'({n}) {name}{h}{d}'

    def __str__(self) -> str:
        return self.user.username

    def init_clean(self):
        if self.is_host is None:
            # if no other players, this player become a host
            self.is_host = not self.game.players_manager

        if self.position is None:
            last = self.game.players_manager.last()
            self.position = last.position + 1 if last else 0

    def clean(self) -> None:
        pass


class PlayerPreform(models.Model):
    """
    Contains users who join the game and wait for the host to approve their joining.
    """

    user: User = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='players_preforms',
    )
    game: Game = models.ForeignKey(
        to=Game,
        on_delete=models.CASCADE,
        related_name='players_preforms',
    )

    class Meta:
        verbose_name = 'user waiting to participate'
        verbose_name_plural = 'users waiting to participate'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique: User could not make many request to join a sigle game. ',
            ),
        ]
