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


class HostCreatePlayer(permissions.BasePermission):
    """
    Host has permition for create Player (take User from UsersJoiningGames to Players)
    """

    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        if not user.is_authenticated or not request.method == 'POST':
            return False

        game, player = view.get_game_and_player()
        if not player or not player.is_host:
            return False

        if not game.stage == stages.SetupStage:
            raise ConflictState(
                f'Admission of participants to the game is not allowed at this stage. ',
                game,
                'invalid_stage',
            )

        return True


class UserDestroyPlayer(permissions.BasePermission):
    """
    Player has permitions for destroy himself (when he leaves game) except host
    (Player may leaves game at any stages. But his bet will be taking anyway and he will win nothing)
    (Host may leaves game only by destroing whole game)
    """

    def has_permission(self, request: Request, view: PlayersViewSet):
        user: User = request.user
        if not user.is_authenticated or not request.method == 'DELETE':
            return False

        user_player = view.get_player()
        if not user_player or user_player.is_host:
            return False

        removing_obj = view.get_object()
        return user_player == removing_obj


# class CreateDestroyPlayers(permissions.BasePermission):
#     """
#     Host has permition for create Player (take User from UsersJoiningGames to Players)

#     Other users has no permitions to change data (only read)
#     """

#     def has_object_permission(
#         self, request: Request, view: PlayersViewSet, obj: Player
#     ):
#         if not request.user.is_authenticated:
#             assert False
#             return False

#         try:
#             game, player = view.get_game_and_player(request)
#         except Exception as e:
#             logger.warning(e)
#             return False

#         if request.method == 'CREATE':
#             return game.stage == stages.SetupStage and player.is_host

#         if request.method == 'DESTROY':
#             return not player.is_host

#         assert False
#         return False


# class IsAuthorAdminModeratorOrReadOnly(permissions.BasePermission):
#     def has_object_permission(self, request, view, obj):
#         if request.method in permissions.SAFE_METHODS:
#             return True
#         if request.method == 'POST':
#             return request.user.is_authenticated
#         return request.user.is_authenticated and (
#             request.user == obj.author
#             or request.user.is_moderator
#             or request.user.is_admin
#         )


# class IsAdminOrReadOnlyPermission(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return (
#             request.method in permissions.SAFE_METHODS
#             or (request.user.is_authenticated and request.user.is_admin)
#             or (request.user.is_authenticated and request.user.is_staff)
#         )
