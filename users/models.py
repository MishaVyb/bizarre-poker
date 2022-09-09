from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as _UserModel
from django.db import models
from core.models import CreatedModifiedModel, FullCleanSavingMixin, UpdateMethodMixin
from core.validators import bet_multiplicity


if TYPE_CHECKING:
    from games.models import Player, PlayerManager
    from ..games.models.game import Game


# not possible to inheritate from get_user_model()
# so we have to use auth user model (_UserModel) directly
class UserProxy(FullCleanSavingMixin, _UserModel):
    players: PlayerManager[Player]  # OneToMany related field initialize by Django
    profile: Profile  # OneToOne related field initialize by Django after Bet creation

    def player_at(self, game: Game) -> Player:
        return self.players.get(game=game)

    def clean(self):
        if not hasattr(self, 'profile'):
            Profile.objects.create(user=self)

    class Meta:
        proxy = True


class Profile(UpdateMethodMixin, FullCleanSavingMixin, CreatedModifiedModel):
    """Model for representing users profile.
    It stores non-auth related information about a site user.
    """

    user: UserProxy = models.OneToOneField(
        UserProxy, on_delete=models.CASCADE, related_name='profile'
    )
    bank: int = models.PositiveIntegerField(
        default=1000,
        validators=[bet_multiplicity],
    )
    """Users money account in cents. Default is 10.00$."""

    def __str__(self) -> str:
        return f'{self.user.username}`s profile'

    def withdraw_money(self, value: int) -> int:
        self.bank -= value
        self.save()
        return value

    def deposit_in(self, value: int):
        self.bank += value
        self.save()

    def clean(self):
        pass


User = UserProxy
"""alias to custom proxy model which extends UserModel behaviour."""

# Note: this poblems goes down after updating to a latest version of Django.
#
# UserProxy is valid model for related relashinships, but you should change migration
# after migrations applyed, otherwise pytest-django falls down:
# `ValueError: Related model 'users.UserProxy' cannot be resolved.`
#
# >>> # to='users.UserProxy'
# >>> to=settings.AUTH_USER_MODEL

UserModel = get_user_model()
"""alias to `real` (not proxy) user model for any reason."""