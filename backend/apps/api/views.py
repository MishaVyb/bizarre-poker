import logging
from functools import cached_property
from operator import attrgetter
from typing import TYPE_CHECKING, Type, TypeAlias
from api import permitions
from api.exceptions import ConflictState

from core.functools.utils import init_logger
from django.shortcuts import get_object_or_404
from games.models import Game, Player
from games.models.player import PlayerPreform
from games.selectors import PlayerSelector
from games.services import actions, stages
from rest_framework import views, viewsets, mixins, exceptions
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    IsAdminUser,
)
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db import models
from api.serializers import (
    BetValueSerializer,
    GameSerializer,
    HiddenPlayerSerializer,
    PlayerPreformSerializer,
    PlayerSerializer,
    ActionSerializer,
)
from users.models import User, DjangoUserModel
from games.services.processors import BaseProcessor

logger = init_logger(__name__)

if TYPE_CHECKING:
    _BASE_VIEW: TypeAlias = viewsets.ViewSet
else:
    _BASE_VIEW = object


class GamesViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self, prefetch_players=True):
        return Game.objects.prefetch_players().all()

    def get_object(self):
        return super().get_object().select_players()

    def perform_create(self, serializer: GameSerializer):
        game: Game = serializer.save()

        # add user as 1st player, user becomes host automatecly
        host = Player.objects.create(user=self.request.user, game=game)
        game.select_players(source=[host])


class GameInterfaceMixin(_BASE_VIEW):
    def get_game(self):
        return (
            Game.objects.prefetch_players().get(pk=self.kwargs['pk']).select_players()
        )

    def get_player(self, game: Game | None = None):
        """
        Get player asociated with game and user from request.
        Return None if no such player.
        """
        game = game or self.get_game()
        user: User = self.request.user
        return user.player_at(game, None)

    def get_game_and_player(self):
        game = self.get_game()
        player = self.get_player(game)
        return (game, player)


class ActionsViewSet(GameInterfaceMixin, viewsets.ViewSet):
    action_url = '/api/v1/games/{game_pk}/actions/{name}/'

    def list(self, request: Request, pk: int):
        user: User = request.user
        game: Game = self.get_game()
        if game.stage.performer != user.player_at(game):
            return Response([])

        possibles = game.stage.get_possible_actions()
        context = {'action_url': self.action_url, 'game_pk': game.pk}
        serializer = ActionSerializer(instance=possibles, many=True, context=context)
        return Response(serializer.data)

    def exicute(
        self,
        action_type: Type[actions.BaseAction],
        *,
        game: Game | None = None,
        by_user: User | None = None,
        **action_kwargs,
    ):
        game = game or self.get_game()

        try:
            action_type.run(game, by_user or self.request.user, **action_kwargs)
        except actions.ActionError as e:
            raise ConflictState(e.action)

        serializer = GameSerializer(instance=game)
        return Response(serializer.data)
        return Response({'latest': game.actions_history[-1]})

    @action(methods=['post'], detail=False)
    def start(self, request: Request, pk: int):
        return self.exicute(actions.StartAction)

    @action(methods=['post'], detail=False)
    def end(self, request: Request, pk: int):
        return self.exicute(actions.EndAction)

    @action(methods=['post'], detail=False, url_path='pass', url_name='pass')
    def pass_action(self, request: Request, pk: int):
        return self.exicute(actions.PassAction)

    @action(methods=['post'], detail=False)
    def bet(self, request: Request, pk: int):
        game = self.get_game()
        context = {'game': game}
        serializer = BetValueSerializer(data=request.data, context=context)
        if serializer.is_valid(raise_exception=True):
            return self.exicute(actions.PlaceBet, game=game, **serializer.data)
        return Response(serializer.errors)

    @action(methods=['post'], detail=False)
    def blind(self, request: Request, pk: int):
        return self.exicute(actions.PlaceBlind)

    @action(methods=['post'], detail=False)
    def check(self, request: Request, pk: int):
        return self.exicute(actions.PlaceBetCheck)

    @action(methods=['post'], detail=False)
    def reply(self, request: Request, pk: int):
        return self.exicute(actions.PlaceBetReply)

    @action(methods=['post'], detail=False)
    def vabank(self, request: Request, pk: int):
        return self.exicute(actions.PlaceBetVaBank)

    @action(
        methods=['post'],
        detail=False,
        # permission_classes=[IsAdminUser],
        url_path='forceContinue',
        url_name='forceContinue',
    )
    def force_continue(self, request: Request, pk: int):
        """
        Force make action for another user to proceed game farther. Taking fist possible
        action for exicution. Mostly for test porpeses.
        """
        assert not request.data, 'applying data to force continue not implemented yet'

        game, player = self.get_game_and_player()
        if game.stage.performer == player:
            logger.warning('Making force action when user can do it by himself. ')

        protos = game.stage.get_possible_actions()
        porotos_without_values = filter(lambda p: not p.action_values, protos)
        try:
            action = next(porotos_without_values).action_class
        except StopIteration:
            raise ConflictState('forceContinue', game)

        return self.exicute(action, game=game, by_user=game.stage.performer.user)


class PlayersViewSet(
    GameInterfaceMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    View represents Players inctances and provides:
    - list and retrieve methods
    - create method (when Host approved User joining)
    - destroy method (when User leaves game)
    """

    lookup_field = 'user__username'
    permission_classes = (
        permitions.ReadOnly
        | permitions.HostCreatePlayer
        | permitions.UserDestroyPlayer,
    )

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_context(self):
        return super().get_serializer_context()

    def get_serializer_class(self):
        """
        Get different serializers to control player hand and combo visability.
        """
        # super().get_serializer_class()
        if not self.request.user.is_authenticated:
            return HiddenPlayerSerializer

        # cards are open at final game stages
        game = self.get_game()
        if game.stage in [stages.OpposingStage, stages.TearDownStage]:
            return PlayerSerializer

        # user can see his cards when getting single object
        obj = self.get_object() if self.action in ['retrieve', 'me'] else None
        if self.get_player(game) == obj:
            return PlayerSerializer

        return HiddenPlayerSerializer

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def perform_create(self, serializer: PlayerSerializer):
        user: User = serializer.validated_data['user']
        game: Game = serializer.validated_data['game']

        if not game.stage == stages.SetupStage:
            raise ConflictState(
                f'Admission of participants to the game is not allowed at this stage. ',
                game,
                'invalid_stage',
            )

        try:
            player_preform = PlayerPreform.objects.get(user=user, game=game)
        except PlayerPreform.DoesNotExist:
            raise exceptions.NotFound('User is not waiting to take part in game. ')

        player_preform.delete()
        return super().perform_create(serializer)  # serializer.save()

    def perform_destroy(self, instance: Player):
        game = instance.game
        if self.get_player(game).is_host and not game.stage == stages.SetupStage:
            raise ConflictState(
                f'Kicking player out of the game is not allowed at this stage. ',
                game,
                'invalid_stage',
            )

        super().perform_destroy(instance)  # instance.delete()
        # after player came out we has to run processing to change game state
        # and only after that save() for other players and game inctance will be called
        BaseProcessor(game).run()

    def perform_authentication(self, request):
        """
        Changing default django user class to custom proxy user class for authenticated
        user for request.
        """
        if isinstance(request.user, DjangoUserModel):
            request.user.__class__ = User

    def get_object(self) -> Player:
        return super().get_object()

    def get_queryset(self):
        return self.get_game().players_manager.all()

    @action(detail=False, methods=['get'], permission_classes=[permitions.UserInGame])
    def me(self, request: Request, pk: int):
        self.kwargs[self.lookup_field] = request.user.username
        return self.retrieve(request)

    @action(detail=False, methods=['get'], permission_classes=[permitions.UserInGame])
    def other(self, request: Request, pk: int):
        other = self.get_game().players.exclude(user=request.user)
        serializer = self.get_serializer(instance=other, many=True)
        return Response(serializer.data)


class PlayersPreformViewSet(
    GameInterfaceMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    View represents futute participants inctances and provides:
    - list and retrieve methods
    - create method (when User trying join Game)
    """

    lookup_field = 'user__username'
    serializer_class = PlayerPreformSerializer
    permission_classes = [
        permitions.UserNotInGame | permitions.ReadOnly & IsAuthenticated
    ]

    def get_queryset(self):
        return PlayerPreform.objects.filter(pk=self.kwargs['pk'])
