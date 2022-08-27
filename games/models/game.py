"""

developing:
[ ] чтобы не надо было вызывать save() каждый раз
[ ] все константы перенести в файл настроек (json файл) и подгружать их с помошью библиотеки для парсинга

"""

from __future__ import annotations

import itertools
from django.db.models import Q
import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Optional, TypeVar
from django.core.exceptions import ValidationError
from core.functools.looptools import circle_after, looptools
from core.functools.utils import StrColors, init_logger
from core.models import CreatedModifiedModel
from django.db import IntegrityError, models
from django.db.models import manager
from django.db.models.query import QuerySet
from django.urls import reverse
from games.backends.cards import CardList, Decks
from games.exeptions import PostRequestRequired
from games.models.fields import CardListField
from ..services import configurations
from ..services.stages import GAME_STAGES_LIST

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

class Game(CreatedModifiedModel):
    objects: GameManager[Game] = GameManager()
    players: PlayerManager[Player]      # OneToMany related field initialize by Django

    deck: CardList = CardListField('deck of cards', blank=True)
    deck_generator: str = models.CharField(
        'name of deck generator method or contaianer',
        max_length=79,
        default=get_deck_default,
    )
    table: CardList = CardListField('cards on the table', blank=True)
    bank: int = models.PositiveIntegerField(
        'sum of all beds has maded for game round', default=0
    )



    begins: bool = models.BooleanField(default=False)
    """Is game started or not."""

    stage_index: int = models.PositiveSmallIntegerField(default=0)
    """key for GAME_STAGES dict"""

    # @property
    # def stage_performer(self) -> Player | None:
    #     # move to custom manager
    #     if self.players.filter(performer=True).exists():
    #         return self.players.get(performer=True) # code get(default=..) method !!!

    #     from ..services.stages import GAME_STAGES_LIST
    #     default_performer = GAME_STAGES_LIST[self.stage_index].default_performer(self)
    #     if default_performer is not None:
    #         default_performer.performer = True
    #         default_performer.save()
    #     return default_performer

    # @stage_performer.setter
    # def stage_performer(self, new_performer: Player | None):
    #     from ..services.stages import GAME_STAGES_LIST
    #     if new_performer is None:
    #         new_performer = GAME_STAGES_LIST[self.stage_index].default_performer(self)

    #     current = self.stage_performer
    #     if current == new_performer:
    #         return

    #     if current is not None:
    #         current.update(performer=False)
    #     if new_performer is not None:
    #         new_performer.update(performer=True)

    @property
    def stage(self) -> BaseGameStage:
        stage_type = GAME_STAGES_LIST[self.stage_index]
        return stage_type(self)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        default_manager_name = 'objects'

    def __init__(
        self,
        *args,
        deck: CardList = None,
        table: CardList = None,
        players: Iterable[User] = [],
        commit: bool = False,
    ) -> None:
        kwargs: dict[str, Any] = {}
        kwargs.setdefault('deck', deck) if deck is not None else ...
        kwargs.setdefault('table', table) if table is not None else ...

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
        for i, user in enumerate(players):
            host = bool(i == 0)
            # self.players.add(
            #     user=user, host=host, dealer=host, position=i
            # )
            self.players.create(
                user=user, game=self, is_host=host, position=i
            )

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


        # CLEAN GAME
        ...

        # CLEAN PLAYERS DEPENDENCES
        if not self.players.exists():
            logger.info('Nothing to clean. Game has no players. ')
            return

        # Player is not defind because not imported (because circular import),
        # so there are a little trick
        Player = self.players.first().__class__
        ...

        # chek stage performer
        # game saving only after game processing raise ProcessingError and waiting for
        # action something from somebody
        if self.stage.performer is None:
            raise IntegrityError(f'{self} has no performer')




