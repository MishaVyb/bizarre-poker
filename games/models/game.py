from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Sequence, TypeVar

from core.functools.utils import StrColors, init_logger
from core.models import CreatedModifiedModel, FullCleanSavingMixin, UpdateMethodMixin
from django.db import models
from django.urls import reverse
from games.models.fields import CardListField
from games.selectors import PlayerSelector
from games.services import configurations
from games.services.cards import CardList
from games.services.stages import BaseGameStage, StagesContainer
from tests.tools import ExtendedQueriesContext

if TYPE_CHECKING:
    from .player import Player, PlayerManager

from users.models import User

logger = init_logger(__name__)


def get_deck_default():
    return configurations.DEFAULT.deck_container_name


_T = TypeVar('_T')


class GameManager(models.Manager[_T]):
    def prefetch_players(self):
        prefetch_lookups = (
            'players_manager',

            # we need to load this:
            # [1] to know player name (for logging) | player.user.username
            # [2] to find a player for user who make Action | user.player_at(game)
            'players_manager__user',

            # we need to load this:
            # [1] to know other players bank wich is max possible value for bet (VaBank)
            # [2] to chance players bank when placing bet or taking benefint
            'players_manager__user__profile',
        )
        # prefetch_related for other side of FogigenKey field (not select_related)
        return super().prefetch_related(*prefetch_lookups)


class Game(UpdateMethodMixin, FullCleanSavingMixin, CreatedModifiedModel):
    objects: GameManager[Game] = GameManager()

    # OneToMany related field initialize by Django
    players_manager: PlayerManager[Player]

    # players -- default is empty selector
    # call init with players to deftine PlayerSelector or call to prefetch_related
    _players_selector: PlayerSelector | None = None

    # test tool
    _db_context: ExtendedQueriesContext | None = None

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

        self.save()  # commit

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
        self, source: Sequence[Player] | None = None, *, force_cashing=False
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

        self._players_selector = PlayerSelector(source, self.players_manager)
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

    @property
    def players(self) -> PlayerSelector:
        if self._players_selector is None:
            raise RuntimeError('None selector. Call for select_players(..) before.')
        return self._players_selector

    def get_players(self) -> PlayerSelector | None:
        """The same as `players` property, but no raises for None value."""
        return self._players_selector

    def clean(self) -> None:
        # [1] validate game properties
        ...

        # [2] validate game stage performer player
        if self._players_selector is None or not self.players:
            return  # nothing to do

        if self.stage.performer is None:
            message = 'Game stage performer is None at cleaning before saving. '
            headline = StrColors.bold(StrColors.red(message))
            logger.warning(
                f'{headline}\n'
                f'{self} should to be saved only after processing raises an error '
                'and wait for some action from some performer. Exception: '
                'when running tests, we have to stop game at different stages. '
            )
