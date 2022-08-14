import logging
from api.serializers import (
    GameSerializer,
    PlayerSerializer,
    PlayerComboSerializer,
    PlayerBetSerializer,
)
from django.shortcuts import get_object_or_404
from games.models import Game, Player, RequirementError
from rest_framework import filters, mixins, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.serializers import BaseSerializer
from games.models.game import HostApprovedGameStart
from users.models import User
from rest_framework.decorators import action
from rest_framework.request import Request
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status
from core.functools.utils import init_logger

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
        # game.players_manager.create(user=user, host=True)

    @action(detail=True, methods=['post'])
    def join(self, request: Request, pk: int | None = None):
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
        #     game.players_manager.create(user=request.user)
        # except IntegrityError as e:
        #     if 'UNIQUE constraint failed' in e.args[0]:
        #         raise

    @action(detail=True, methods=['post'])
    def start(self, request: Request, pk: int | None = None):
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
