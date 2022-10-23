from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Iterable, Sequence

from core.models import (
    CreatedModifiedModel,
    FullCleanSavingMixin,
    UpdateMethodMixin,
    get_list_default,
)
from core.utils import StrColors, init_logger
from django.db import models
from django.urls import reverse
from games.configurations.configurations import CONFIG_SCHEMAS, ConfigChoices
from games.models.fields import CardListField
from games.models.managers import GameManager

from games.selectors import PlayerSelector
from games.services.cards import CardList
from games.services.processors import BaseProcessor
from users.models import User

if TYPE_CHECKING:
    from .player import Player, PlayerManager, PlayerPreform


logger = init_logger(__name__)


class Game(UpdateMethodMixin, FullCleanSavingMixin, CreatedModifiedModel):
    objects: GameManager[Game] = GameManager()

    # OneToMany related fields initialized by Django
    players_manager: PlayerManager[Player]
    players_preforms: models.Manager[PlayerPreform]

    # players -- default is empty selector
    # call init with players to deftine PlayerSelector or call to prefetch_related
    _players_selector: PlayerSelector | None = None

    @property
    def players(self) -> PlayerSelector:
        if self._players_selector is None:
            detail = 'Call for select_players(..) before. They will be selected here. '
            logger.warning(StrColors.yellow('None selector.') + detail)
            self.select_players(force_cashing=True, force_prefetching=True)
            return self.players
        return self._players_selector


    config_name: str = models.CharField(
        choices=ConfigChoices.choices,
        max_length=30,
        default=ConfigChoices.CLASSIC,
    )
    deck: CardList = CardListField(blank=True)
    table: CardList = CardListField(blank=True)
    bank: int = models.PositiveIntegerField(default=0)

    @property
    def bank_total(self):
        return self.bank + self.players.aggregate_sum_all_bets()

    actions_history: list[dict[str, Any]] = models.JSONField(
        default=get_list_default,
        blank=True,
    )
    """
    List with actions and stages that have been proceed:
    >>> [{'performer': str | None, 'class': str, 'message': str}, ...]

    (for stages performer is None)
    """

    begins: bool = models.BooleanField(default=False)
    rounds_counter: int = models.PositiveIntegerField(default=1)
    stage_index: int = models.PositiveSmallIntegerField(default=0)

    @property
    def stage(self):
        stage_class = self.stages[self.stage_index]
        return stage_class(self)

    @cached_property
    def stages(self):
        return self.config.stages

    @cached_property
    def config(self):
        return CONFIG_SCHEMAS[self.config_name]

    def get_processor(self, *, autosave: bool = True) -> BaseProcessor:
        """
        Simple shorcut for getting processor assotiated with this game.
        Usefull for BaseAction.run(..).
        """
        return BaseProcessor(self, autosave=autosave)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        default_manager_name = 'objects'

    def __init__(
        self, *args, players: Iterable[User] = [], commit: bool = False, **kwargs
    ) -> None:
        assert not (kwargs and args), 'not supported together'
        assert commit if players else True, (
            'django obligates to save a model instance'
            'before using it in related relashinships'
        )

        super().__init__(*args, **kwargs)

        if not commit:
            return

        self.save()

        if not players:
            return

        prefetched_players: list[Player] = []
        for user in players:
            # it`s better to call there for Player(..) and bulk create
            # but Player is not imported here because of circelar imports
            new_player = self.players_manager.create(user=user, game=self)
            prefetched_players.append(new_player)

        # UPDATE PLAYER CONTAINER
        # the same as self.select_players,
        # but we don`t need hint db because we know players
        self.select_players(prefetched_players)

    def __repr__(self) -> str:
        try:
            return f'({self.pk}) game at [#{self.stage_index}] {self.stage}'
        except Exception:
            return f'{self.__class__.__name__} ({self.pk})'

    def __str__(self) -> str:
        return StrColors.underline(self.__repr__())

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})

    def select_players(
        self,
        source: Sequence[Player] | None = None,
        *,
        force_cashing=False,
        force_prefetching=False,
    ):
        """Call to update `self.players`.

        After player was prefetched at `PlayerManager` call for this to re-define
        selector's source. Or pass source directly if you know the list of players to
        avoid excess db evulation.

        It could be used without calling `prefetch_related(..)`, but it makes new query
        to db. After first query - source will be cached, but you may force cashing it
        (for players index access).

        return `self`
        """
        if force_prefetching:
            lookup = 'user__profile'
            default_source = self.players_manager.prefetch_related(lookup).all()
        else:
            default_source = self.players_manager.all()

        if force_cashing:
            # it's wierd make cashe for source
            # (it already should be as `real` data, not prepared QuerySet)
            assert not source
            [p for p in default_source]  # force cache

        if source is None:
            # do not call for source.__bool__()
            # because it well evulte db inside to check is QuerySet empty or not
            source = default_source

        self._players_selector = PlayerSelector(source)
        return self

    def reselect_players(self):
        """from new query to db"""
        previous_len = len(self.players)

        if hasattr(self, '_prefetched_objects_cache'):
            self._prefetched_objects_cache.pop('players_manager')
        else:
            raise RuntimeError('There are no prefetched cashe. Nothing to re-select.  ')

        # we already know game, so we won't accessing Game.objects
        # using selectr_related through players_manager, not prefetch_related
        # because anyway we will cashe qs, so it`s better make 1 query then 3
        # (1- for players 2- for users 3- for user.profiles)
        qs = self.players_manager.select_related('user__profile')

        # just update selected players at this game instance
        # in this case we need force_cashing for index acsessing
        [p for p in qs]
        self.select_players(qs)

        if len(self.players) == previous_len:
            raise RuntimeError(
                'Players amount wasn`t change. '
                'There was no reason call for reselect_players(). '
            )

    def get_players(self) -> PlayerSelector | None:
        """The same as `players` property, but no raises for None value."""
        return self._players_selector

    def clean(self) -> None:
        pass
