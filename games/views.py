"""

developing:
[ ] apply @decorators.login_required

"""
from collections import OrderedDict
from copy import copy
import itertools
import math
from pprint import pformat, pprint
from typing import Any
from rest_framework.response import Response
from core.functools.decorators import temporally
from core.functools.utils import init_logger
from core.types import JSON, _JSON_SUPPORTED
from django import views
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.list import ListView
from poker import settings
from users.models import User
from api import views as api_views
from games import models
from games.models import PlayerBet
from games.services.cards import Card
from rest_framework.test import APIClient
from api.serializers import GameSerializer, PlayerSerializer
from django.urls import reverse

from games.services.configurations import DEFAULT
from core.functools.looptools import looptools

logger = init_logger(__name__)
app_name = 'games'


class IndexView(views.View):
    template = 'games/index.html'
    title = ''

    @temporally(Card.Text, str_method='classic')
    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponse:
        """handling GET request"""

        context = {}
        if request.user.is_authenticated:
            context['user_games'] = models.Game.objects.prefetch_players().filter(
                players_manager__user=self.request.user
            )
            context['not_user_games'] = models.Game.objects.prefetch_players().exclude(
                players_manager__user=self.request.user
            )
        else:
            context['not_user_games'] = models.Game.objects.all()

        for game in itertools.chain(
            context.get('user_games', []), context.get('not_user_games', [])
        ):
            game.select_players()

        return render(request, self.template, context)


class UserGamesListView(ListView):
    context_object_name = 'games'

    def get_queryset(self):
        return models.Game.objects.filter(players__user=self.request.user)


class GameView(views.View):
    name = 'game'
    namespace_name = app_name + ':' + name
    template = 'games/game.html'
    title = ''

    #
    @temporally(Card.Text, str_method='classic')
    def get(self, request: WSGIRequest, pk: int) -> HttpResponse:
        """handling GET request"""
        # return HttpResponse()
        # client = APIClient()
        # client.force_login(request.user)
        # game_response = client.get(f'/api/v1/games/{pk}/')
        response: Response = api_views.GamesViewSet.as_view({'get': 'retrieve'})(
            request, pk=pk
        )
        game: dict = response.data

        response = api_views.PlayersViewSet.as_view({'get': 'me'})(request, game_pk=pk)
        if response.status_code != 200:
            raise RuntimeError(f'Response error: {response.data}')
        player: dict = response.data

        response = api_views.PlayersViewSet.as_view({'get': 'other'})(
            request, game_pk=pk
        )
        if response.status_code != 200:
            raise RuntimeError(f'Response error: {response.data}')
        other_players: list = response.data

        response = api_views.ActionsViewSet.as_view({'get': 'list'})(request, pk=pk)
        if response.status_code != 200:
            raise RuntimeError(f'Response error: {response.data}')
        actions: dict = response.data

        # self.make_log(game=game, player=player, other_players=other_players, actions=actions)

        # re-format a little bit
        # [1] game
        self.reformat_game(game)

        # [2] players
        self.reformat_player(player)
        for p in other_players:
            self.reformat_player(p)

        # [3] actions
        BUTTON_CLASSES = {
            'pass': 'btn btn-danger',
            'check': 'btn btn-outline-success',
            'reply': 'btn btn-outline-success',
            'blind': 'btn btn-outline-success',
            'start': 'btn btn-info',
            'end': 'btn btn-info',
            'vabank': 'btn btn-success',
            'place bet': 'btn btn-outline-success',
            'next': 'btn btn-primary',
        }
        avaliable: list = actions['avaliable']

        if avaliable and avaliable[0]['name'] == 'bet':
            avaliable[0]['name'] = 'place bet'
            min = avaliable[0]['values']['min']
            max = avaliable[0]['values']['max']
            avaliable.pop(0)

            for extra in [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200]:
                if min <= extra <= max:
                    pk = game['id']
                    avaliable.append(
                        {
                            'name': '💵 {bet:.2f}'.format(bet=extra/100),
                            'url': f'/api/v1/games/{pk}/actions/bet_{extra}/',
                        }
                    )

        if player['is_host']:
            avaliable.append({'name': 'next'})

        for action in avaliable:
            action['bet_values'] = action.get('values')
            action['button_class'] = BUTTON_CLASSES.get(action['name'], 'btn btn-outline-success')

        context = {
            'game': game,
            'player': player,
            'other_players': other_players,
            'actions': avaliable,
        }

        return render(request, self.template, context)

    def reformat_game(self, game: JSON):
        assert isinstance(game, dict)
        n = int(game.get('bank', 0) / DEFAULT.bet_multiplicity)
        game['bank'] = '🍔 ' * n
        game['actions_history'] = list(reversed(game['actions_history']))
        for action in game['actions_history']:

            if action['performer'] is None:
                badge_class = 'badge bg-info'
            elif action['performer'] == self.request.user.username:
                badge_class = 'badge bg-warning'
            else:
                badge_class = 'badge bg-dark'

            if action['class'] == 'OpposingStage':
                badge_class = 'badge bg-success'

            action['badge_class'] = badge_class

    def reformat_player(self, player: JSON | _JSON_SUPPORTED):
        assert isinstance(player, dict)
        if not player['bets']:
            player['bet_total'] = ''
        else:
            n = int(player['bet_total'] / DEFAULT.bet_multiplicity)
            player['bet_total'] = '🍔 ' * n or 'check'

        bank = player['profile_bank']
        player['profile_bank'] = '💵 {bank:.2f}'.format(bank=player['profile_bank']/100)

    def make_log(self, data_dict: JSON = None, **kwargs):
        data = copy(data_dict or kwargs)
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, OrderedDict):
                    data[i] = dict(item)
        else:
            for key, item in data.items():
                if isinstance(item, OrderedDict):
                    data[key] = dict(item)
                elif isinstance(item, list):
                    for i__, item__ in enumerate(item):
                        if isinstance(item__, OrderedDict):
                            item[i__] = dict(item__)
        data_str = pformat(data, width=50, sort_dicts=False)
        logger.info(f'\n{data_str}')

    def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        game.select_players(force_cashing=True, force_prefetching=True)

        auto.autoplay_game(game, stop_after_actions_amount=1)
        return redirect(self.namespace_name, pk=pk)


# class MakePlayerBetView(views.View):
#     name = 'bet'
#     full_name = app_name + ':' + name

#     def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
#         game: models.Game = get_object_or_404(models.Game, pk=pk)
#         player: models.Player = request.user.players.get(game=game)

#         form = PlayerBetForm(data=request.POST, instance=player.bet)

#         if form.is_valid():
#             form.save()
#             logger.info('form saved')
#             # bet: PlayerBet = form.save(commit=False)
#             # bet.player = player
#             # bet.save()

#         return redirect(GameView.namespace_name, pk=pk)
