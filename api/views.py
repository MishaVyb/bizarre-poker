from functools import cached_property
import logging
from typing import Type
from api.serializers import (
    BetValueSerializer,
    GameSerializer,
    PlayerSerializer,
)
from django.shortcuts import get_object_or_404, get_list_or_404
from games.models import Game, Player
from rest_framework import filters, mixins, viewsets, views
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.serializers import BaseSerializer
from rest_framework.exceptions import NotFound

from users.models import User
from rest_framework.decorators import action
from rest_framework.request import Request
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status
from core.functools.utils import init_logger
from django.db.models import Q
from games.selectors import PlayerSelector
from core.functools.decorators import temporally
from games.services.cards import Card
from django.shortcuts import get_object_or_404, redirect, render

logger = init_logger(__name__, logging.INFO)
from games.services import actions


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

    @action(methods=['post'], detail=False)
    def test_action(self, request):
        return Response({'dsaf': 'sadgf'})


class ActionsViewSet(viewsets.ViewSet):
    action_urls: dict[Type[actions.BaseGameAction], str] = {
        actions.StartAction: '/api/v1/games/{pk}/actions/start/',
        actions.PassAction: '/api/v1/games/{pk}/actions/pass/',
        actions.PlaceBlind: '/api/v1/games/{pk}/actions/blind/',
        actions.PlaceBet: '/api/v1/games/{pk}/actions/bet/',
        actions.PlaceBetCheck: '/api/v1/games/{pk}/actions/check/',
        actions.PlaceBetReply: '/api/v1/games/{pk}/actions/reply/',
        actions.PlaceBetVaBank: '/api/v1/games/{pk}/actions/vabank/',
    }

    @cached_property
    def action_names(self) -> dict[Type[actions.BaseGameAction], str]:
        result: dict[Type[actions.BaseGameAction], str] = {}
        result[actions.StartAction] = 'actions'
        for key, url in self.action_urls.items():
            result[key] = next(filter(None, reversed(url.split('/'))))
        return result

    def get_object(self):
        return Game.objects.prefetch_players().get(**self.kwargs).select_players()

    def get_actions_representation(self):
        assert len(actions.ActionContainer.actions) == len(self.action_urls)

        game: Game = self.get_object()
        result = actions.ActionContainer.get_avaliable_and_not(game, self.request.user)
        avaliable, not_avaliable, excess = result

        # make representation
        avaliable_repr = []
        for action_type in avaliable:
            action_detail = {}
            action_detail['name'] = self.action_names[action_type]
            action_detail['url'] = self.action_urls[action_type].format(**self.kwargs)
            if action_type.values:
                action_detail['values'] = action_type.values
            avaliable_repr.append(action_detail)

        not_avaliable_repr = []
        for action_type in not_avaliable:
            action_detail = {}
            action_detail['name'] = self.action_names[action_type]
            action_detail['url'] = self.action_urls[action_type].format(**self.kwargs)
            action_detail['error'] = str(action_type.error)
            not_avaliable_repr.append(action_detail)

        excess_repr = []
        for action_type in excess:
            action_detail = {}
            action_detail['name'] = self.action_names[action_type]
            action_detail['url'] = self.action_urls[action_type].format(**self.kwargs)
            excess_repr.append(action_detail)

        return {
            'avaliable': avaliable_repr,
            'not_avaliable': not_avaliable_repr,
            'excess': excess_repr,
        }

    def list(self, request, pk: int):
        return Response(self.get_actions_representation())

    def exicute(self, action_type: Type[actions.BaseGameAction], **action_kwargs):
        game = self.get_object()

        try:
            action_type(game, self.request.user, **action_kwargs)
        except actions.ActError as e:
            return Response({'act_error': str(e)})

        serializer = GameSerializer(instance=game)
        return redirect('games:game', pk=self.kwargs['pk'])
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def start(self, request, pk: int):
        return self.exicute(actions.StartAction)

    @action(methods=['post'], detail=False, url_path='pass', url_name='pass')
    def pass_action(self, request, pk: int):
        return self.exicute(actions.PassAction)

    @action(methods=['post'], detail=False)
    def blind(self, request, pk: int):
        return self.exicute(actions.PlaceBlind)

    @action(methods=['post'], detail=False)
    def bet(self, request, pk: int):
        serializer = BetValueSerializer(data=request.data)
        if serializer.is_valid():
            return self.exicute(actions.PlaceBet, **serializer.data)
        return Response(serializer.errors)

    @action(methods=['post'], detail=False)
    def check(self, request, pk: int):
        return self.exicute(actions.PlaceBetCheck)

    @action(methods=['post'], detail=False)
    def reply(self, request, pk: int):
        return self.exicute(actions.PlaceBetReply)

    @action(methods=['post'], detail=False)
    def vabank(self, request, pk: int):
        return self.exicute(actions.PlaceBetVaBank)



class PlayersViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlayerSerializer

    def get_queryset(self):
        game_pk = self.kwargs['game_pk']
        return Player.objects.filter(game=game_pk)

    @action(detail=False, methods=['get'])
    def me(self, request: Request, game_pk: int):
        me = get_object_or_404(Player, game=game_pk, user=request.user)
        serializer = PlayerSerializer(instance=me, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def other(self, request: Request, game_pk: int):
        other = Player.objects.filter(game=game_pk).exclude(user=request.user)
        serializer = PlayerSerializer(
            instance=other, context={'request': request}, many=True
        )
        return Response(serializer.data)


# class ActionsView(views.APIView):

#     def get()


class TestView(views.APIView):
    def get(self, request):
        return Response(
            {
                'user': repr(request.user),
                'user_type': repr(type(request.user)),
            }
        )
