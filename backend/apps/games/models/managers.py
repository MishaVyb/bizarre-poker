from __future__ import annotations

from typing import TypeVar

from core.models import IterableManager, related_manager_method
from core.utils import init_logger
from django.db import models

logger = init_logger(__name__)
_T = TypeVar('_T')


class GameManager(models.Manager[_T]):
    def prefetch_players(self):
        """
        Call to prefetch all nessaccery related data to handling players.
        Then call for game.select_players(..) method to initialize selector.
        """
        # [NOTE] we have to:
        #
        # prefetch 'players_manager' because:
        # [1] to know player name (for logging) | player.user.username
        # [2] to find a player for user who make Action | user.player_at(game)
        #
        # prefetch 'players_manager__user' because:
        # [1] to know other players bank wich is max possible value for bet (VaBank)
        # [2] to chance players bank when placing bet or taking benefint
        #
        # and 'players_manager__user__profile'.
        prefetch_lookups = (
            'players_manager',
            'players_manager__user',
            'players_manager__user__profile',
        )
        return super().prefetch_related(*prefetch_lookups)


class PlayerQuerySet(models.QuerySet):
    pass


class PlayerManager(IterableManager[_T]):
    def get_queryset(self):
        return PlayerQuerySet(
            model=self.model,
            using=self._db,
            hints=self._hints,
        ).order_by('position')

    @related_manager_method
    def update_annotation(self, *fields, **fields_values):
        """Update annotaion for every player."""
        for field in fields:
            raise NotImplementedError('Load value from db is not implemented yet. ')

        for field, value in fields_values.items():
            for player in self:
                setattr(player, field, value)

    @property  # type: ignore
    @related_manager_method
    def after_dealer(self):
        """active players starting after dealer button."""
        dealer_case = models.Case(
            models.When(position=0, then=models.Value(True)),
            models.When(position__gt=0, then=models.Value(False)),
        )
        return (
            self.annotate(dealer=dealer_case)
            .order_by('dealer', 'position')
            .filter(is_active=True)
        )

    @property  # type: ignore
    @related_manager_method
    def after_dealer_all(self):
        """All players (active and passive) starting after dealer button."""
        return self.order_by('is_dealer', 'position')

    @property  # type: ignore
    @related_manager_method
    def active(self):
        """Players that have not said `pass`."""
        return self.filter(is_active=True)

    @property  # type: ignore
    @related_manager_method
    def host(self):
        return self.get(is_host=True)

    @property  # type: ignore
    @related_manager_method
    def dealer(self):
        return self.get(is_dealer=True)
