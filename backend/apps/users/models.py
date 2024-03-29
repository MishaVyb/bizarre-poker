from __future__ import annotations

from typing import TYPE_CHECKING, Type, TypeAlias, TypeVar, overload

from django.contrib.auth.models import UserManager
from django.contrib.auth.models import User as _DjangoUserModel
from django.db import models
from core.models import CleanManagerMixin, CreatedModifiedModel, FullCleanSavingMixin
from core.utils.types import NOT_PROVIDED


if TYPE_CHECKING:
    from games.models.managers import PlayerManager
    from games.models import Player
    from ..games.models.game import Game


_T = TypeVar('_T')

class UserProxyManager(CleanManagerMixin, UserManager[_T]):
    pass

class UserProxy(FullCleanSavingMixin, _DjangoUserModel):
    players: PlayerManager[Player]
    profile: Profile
    objects: UserProxyManager[UserProxy] = UserProxyManager()

    REQUIRED_FIELDS = ['profile', 'is_staff']

    @overload
    def player_at(self, game: Game) -> Player:
        ...

    @overload
    def player_at(self, game: Game, default: _T | NOT_PROVIDED) -> Player | _T:
        ...

    def player_at(
        self, game: Game, default: _T | Type[NOT_PROVIDED] = NOT_PROVIDED
    ) -> Player | _T:
        if default is NOT_PROVIDED:
            return game.players.get(user=self)
        try:
            return game.players.get(user=self)
        except StopIteration:
            return default  # type: ignore

    def post_init_clean(self):
        Profile.objects.create(user=self)

    class Meta:
        proxy = True


class Profile(FullCleanSavingMixin, CreatedModifiedModel):
    """
    Model for representing users profile.
    It stores non-auth related information about a site user.
    """

    user: UserProxy = models.OneToOneField(
        UserProxy, on_delete=models.CASCADE, related_name='profile'
    )
    bank: int = models.PositiveIntegerField(default=1000)
    """Users money account. Default is 1000$."""

    def __str__(self) -> str:
        return f'{self.user.username}`s profile'

    def clean(self):
        pass


User: TypeAlias = UserProxy
"""
Alias to custom `proxy` model which extends DjangoUserModel behaviour.
"""

DjangoUserModel: TypeAlias = _DjangoUserModel
"""
Alias to `real` (not proxy) user model for any reason.
"""
