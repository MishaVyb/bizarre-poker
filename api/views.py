import logging
from api.serializers import (
    GameSerializer,
    PlayerSerializer,
    PlayerComboSerializer,
    PlayerBetSerializer,
)
from django.shortcuts import get_object_or_404
from games.models import Game, Player
from rest_framework import filters, mixins, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.serializers import BaseSerializer

from users.models import User
from rest_framework.decorators import action
from rest_framework.request import Request
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status
from core.functools.utils import init_logger
from django.db.models import Q

logger = init_logger(__name__, logging.INFO)


class GamesViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer: GameSerializer):
        game = serializer.save()

        # make_user_as_host
        user = serializer.context['request'].user
        Player.objects.create(user=user, game=game, host=True)
        # game.players.create(user=user, host=True)

    @action(detail=True, methods=['post'])
    def join(self, request: Request, pk: int):
        game: Game = self.get_object()
        serializer = PlayerSerializer(
            data={
                'game': pk,
                'user': request.user,
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'status': f'{request.user.username} joined {game}'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # try:
        #     game.players.create(user=request.user)
        # except IntegrityError as e:
        #     if 'UNIQUE constraint failed' in e.args[0]:
        #         raise

    @action(detail=True, methods=['post'])
    def start(self, request: Request, pk: int):
        game: Game = self.get_object()
        player = game.players.get(user=request.user)
        try:
            game.continue_processing()
        except RequirementError as e:
            if not e.requirement == HostApprovedGameStart:
                message = f'{game} are not waiting for start action (probably already started)'
                logger.warning(message)
                return Response(
                    {'status': message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if e.satisfier == player:
                logger.info(f'{e.requirement} succsessfuly satisfyed')
                e.requirement.satisfy()
                return Response({'status': f'{game} started'})
            else:
                logger.warning(f'no satisfaction for {e.requirement}')
                return Response(
                    {'status': f'Only host can start games'},
                    status=status.HTTP_403_FORBIDDEN,
                )

    # @action(detail=True, methods=['post'])
    # def bet(self, request: Request, pk: int):
    #     raise NotImplementedError
    #     game: Game = self.get_object()
    #     player = game.players.get(user=request.user)
    #     value = request.data['value']
    #     player.bet.place(value)


class PlayersViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset = Game.objects.all()
    serializer_class = PlayerSerializer
    # pagination_class = LimitOffsetPagination

    def get_queryset(self):
        game_pk = self.kwargs['game_pk']
        return Player.objects.filter(game=game_pk)

    @action(detail=False, methods=['get'])
    def user(self, request: Request, game_pk: int):
        game: Game = get_object_or_404(Game, pk=game_pk)
        player: Player = request.user.players.get(game=game)
        serializer = PlayerSerializer(instance=player, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def other(self, request: Request, game_pk: int):
        game: Game = get_object_or_404(Game, pk=game_pk)
        players = game.players.filter(~Q(user=request.user))
        serializer = PlayerSerializer(
            instance=players, many=True, context={'request': request}
        )
        return Response(serializer.data)


class BetViewSet(
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
    ):
    """Avalibalbe only update bet value.
    None is default (no bids was placed)
    0 (zero) is for "pass"
    positive integer < user.bank possible balue
    """
    serializer_class = PlayerBetSerializer

    def get_queryset(self):
        game_pk = self.kwargs['game_pk']
        return Player.objects.filter(game=game_pk)