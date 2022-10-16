from __future__ import annotations
from typing import TYPE_CHECKING

from rest_framework import permissions, views
from rest_framework.request import Request
from api.exceptions import ConflictState
from core.functools.utils import init_logger
from users.models import User

from games.models.player import Player
from games.services import stages

if TYPE_CHECKING:
    from api.views import PlayersViewSet

logger = init_logger(__name__)


class ReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: views.APIView):
        return request.method in permissions.SAFE_METHODS


class UserInGame(permissions.BasePermission):
    """
    Permition for GET `players/me` and `players/other`
    """

    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        return user.is_authenticated and view.get_player()


class UserNotInGame(permissions.BasePermission):
    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        return user.is_authenticated and not view.get_player()


class HostCreatePlayer(permissions.BasePermission):
    """
    Host has permition for create Player (take User from UsersJoiningGames to Players).
    """

    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        if not user.is_authenticated or not request.method == 'POST':
            return False

        player = view.get_player()
        if not player or not player.is_host:
            return False

        return True


class UserDestroyPlayer(permissions.BasePermission):
    """
    - Player has permitions for destroy himself (when he leaves game).
    - Player may leaves game at any stages, but his bet will be taking anyway.
    - Host has not permissions to destroy himself, but he could destroy any other player
    on SetupStage (kick a player out of the game).
    - Host may leaves game only by destroing whole game.
    """

    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        if not user.is_authenticated or not request.method == 'DELETE':
            return False

        user_player = view.get_player()
        if not user_player:
            return False

        removing_obj = view.get_object()
        return (user_player == removing_obj and not user_player.is_host) or (
            user_player.is_host and not user_player == removing_obj
        )
