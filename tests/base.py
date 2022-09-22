from __future__ import annotations

import pytest
from core.functools.utils import init_logger
from games.models import Game, Player
from users.models import User

logger = init_logger(__name__)


@pytest.mark.usefixtures('setup_users')
class BaseGameProperties:
    usernames = ('vybornyy', 'simusik', 'barticheg')
    game_pk: int

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    # we use not cahced property to force test assertion compare real db value with
    # expected result (the same for other)
    @property
    def game(self) -> Game:
        """Game with prefetched players at manager and with players selector.

        Note:
        it makes new query evry time(!) so it will be another game instanse every time.
        """
        return (
            Game.objects.prefetch_players()
            .get(pk=self.game_pk)
            .select_players(force_cashing=True)
        )

    @property
    def players(self) -> dict[str, Player]:
        return {
            user.username: user.players.get(game=self.game) for user in self.users_list
        }

    @property
    def players_list(self) -> list[Player]:
        return [user.players.get(game=self.game) for user in self.users_list]

    def __str__(self) -> str:
        return self.__class__.__name__
