from __future__ import annotations

import pytest
from core.functools.utils import StrColors, init_logger, logging
from games.models import Game, Player
from games.services import actions
from games.services.actions import ActError, ActionContainer
from games.services.stages import StagesContainer
from users.models import User

logger = init_logger(__name__, logging.DEBUG)


def param_kwargs(_id: str = None, _marks=(), **kwargs: object):
    """Usage:

    >>> pytets.fuxture(params=[
            param_kwargs(...),
            param_kwargs(...),
            ...
        ])
    """
    return pytest.param(dict(**kwargs), marks=_marks, id=_id)


def param_kwargs_list(_id: str = None, _marks=(), **kwargs: object):
    """Usage:

    >>> pytets.mark.parametrize('attr_one, attr_two, attr_other, ..', [
            param_kwargs_list(..),
            param_kwargs_list(..),
            ...
        ])
    """
    return pytest.param(*kwargs.values(), marks=_marks, id=_id)


@pytest.mark.usefixtures('setup_users')
class BaseGameProperties:
    usernames = ('vybornyy', 'simusik', 'barticheg')  # host username is 'vybornyy'
    game_pk: int

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self.game_pk)

    @property
    def players(self) -> dict[str, Player]:
        return {p.user.username: p for p in self.game.players}

    @property
    def players_list(self) -> list[Player]:
        return [user.player_at(self.game) for user in self.users_list]


    def __str__(self) -> str:
        return self.__class__.__name__
