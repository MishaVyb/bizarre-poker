from typing import Sequence

from django import template
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser

from games import models

register = template.Library()
User = get_user_model()


@register.filter
def player(game: models.Game, user: AbstractBaseUser):
    try:
        return game.players.get(user=user)
    # except game.DoesNotExist:
    except Exception:
        return None


@register.filter
def hand(player: models.Player):
    if isinstance(player, models.Player):
        return player.hand
    else:
        return player


@register.filter
def index(indexable: Sequence, i: int):
    return indexable[i]
