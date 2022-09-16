from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, TypeVar

from core.functools.utils import StrColors, init_logger
from core.models import (CreatedModifiedModel, FullCleanSavingMixin,
                         UpdateMethodMixin)
from django.db import models
from django.urls import reverse
from games.services.cards import CardList
from games.models.fields import CardListField

from ..services import configurations
from ..services.stages import StagesContainer

if TYPE_CHECKING:
    from .player import Player, PlayerManager
    from ..services.stages import BaseGameStage

from users.models import User

logger = init_logger(__name__, logging.INFO)


def get_deck_default():
    return configurations.DEFAULT.deck_container_name


_T = TypeVar('_T')


class GameManager(models.Manager[_T]):
    pass


class Game(UpdateMethodMixin, FullCleanSavingMixin, CreatedModifiedModel):
    objects: GameManager[Game] = GameManager()
    players: PlayerManager[Player]  # OneToMany related field initialize by Django

    deck: CardList = CardListField('deck of cards', blank=True)
    deck_generator: str = models.CharField(
        'name of deck generator method or contaianer',
        max_length=79,
        default=get_deck_default,
    )
    table: CardList = CardListField('cards on the table', blank=True)
    bank: int = models.PositiveIntegerField(
        'all accepted beds for game round', default=0
    )

    begins: bool = models.BooleanField(default=False)
    """Is game started or not."""

    stage_index: int = models.PositiveSmallIntegerField(default=0)
    """key for GAME_STAGES dict"""

    @property
    def stage(self) -> BaseGameStage:
        stage_type = StagesContainer.stages[self.stage_index]
        return stage_type(self)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        default_manager_name = 'objects'

    def __init__(
        self,
        *args,
        players: Iterable[User] = [],
        commit: bool = False,
        **kwargs
    ) -> None:
        assert not (
            kwargs and args
        ), f'not supported args and kwargs toogether. {args=}, {kwargs=}'

        super().__init__(*args, **kwargs)

        if commit:
            self.save()
        assert not players if not commit else True, (
            'django obligates to save a model instance'
            'before using it in related relashinships'
        )
        for user in players:
            self.players.create(user=user, game=self)

    def __repr__(self) -> str:
        try:
            return f'({self.pk}) game at [#{self.stage_index}] {self.stage}'
        except Exception:
            return f'{self.__class__.__name__} ({self.pk})'

    def __str__(self) -> str:
        return StrColors.underline(self.__repr__())

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})

    def clean(self) -> None:
        if self.players and self.stage.performer is None:
            # raise IntegrityError(f'{self} has no performer')
            message = 'Game stage performer is None at cleaning before saving. '
            headline = StrColors.bold(StrColors.red(message))
            logger.warning(
                f'{headline}\n'
                f'{self} should to be saved only after processing raises an error '
                'and wait for some action from some performer. Exception: '
                'when running tests, we have to stop game at different stages. '
            )

        # move to player constraints (?)
        if str(self.stage) == 'SetupStage':
            if any(p.hand for p in self.players):
                logger.warning(
                    f'Some player has cards in hand at {self}. Clearing them. '
                )
                for p in self.players:
                    p.hand.clear()
                    p.save()

            if any(not p.is_active for p in self.players):
                logger.warning(
                    f'Some player is passed at {self}. Making all players active. '
                )
                for p in self.players:
                    p.update(is_active=True)

            if self.table:
                logger.warning(f'Table is not empty at {self}. Clearing it. ')
                for p in self.players:
                    p.update(is_active=True)

            if self.bank:
                logger.error(f'Bank is not empty at {self}. ')
                raise NotImplementedError
