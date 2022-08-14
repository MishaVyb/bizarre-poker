from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as _UserModel
from django.db import models
from django.db.models import manager
from django.db.models.query import QuerySet

if TYPE_CHECKING:
    from games.models import Player

# not possible to inheritate from get_user_model()
# so we have to use auth user model (_UserModel) directly
class UserProxy(_UserModel):
    @property
    def players(self) -> QuerySet[Player]:
        return self._players.all()

    @property
    def players_manager(self) -> manager.RelatedManager:
        return self._players

    @property
    def players_manager(self) -> manager.RelatedManager:
        return self._players

    @property
    def profile(self) -> Profile:
        if hasattr(self, '_profile'):
            return self._profile
        return Profile.objects.create(user=self)

    class Meta:
        proxy = True


class Profile(models.Model):
    """Model for representing users profile.
    It stores non-auth related information about a site user.
    """

    user: UserProxy = models.OneToOneField(
        UserProxy, on_delete=models.CASCADE, related_name='_profile'
    )
    bank: int = models.PositiveIntegerField(default=1000)
    """Users money account in cents. Default is 10.00$."""


User = UserProxy
"""alias to custom proxy model which extends UserModel behaviour.

WARNING!
UserProxy is valid model for related relashinships, but you should change migration file
after migrations applyed, otherwise pytest-django falls down:
`ValueError: Related model 'users.UserProxy' cannot be resolved.`


>>> # to='users.UserProxy'
>>> to=settings.AUTH_USER_MODEL
"""

UserModel = get_user_model()
"""alias to `real` (not proxy) user model for any reason."""
