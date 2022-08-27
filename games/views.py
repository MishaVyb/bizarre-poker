"""

developing:
[ ] apply @decorators.login_required

"""
from pprint import pformat, pprint
from typing import Any

from core.functools.decorators import temporally
from core.functools.utils import init_logger
from django import views
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.list import ListView
from poker import settings
from users.models import User

from games import models
from games.models import PlayerBet
from games.backends.cards import Card

from api.serializers import GameSerializer, PlayerSerializer
from django.urls import reverse

logger = init_logger(__name__)
app_name = 'games'


class IndexView(views.View):
    template = 'games/index.html'
    title = ''

    @temporally(Card.Text, str_method='classic')
    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponse:
        """handling GET request"""
        if request.user.is_authenticated:
            context = {
                'not_user_games': models.Game.objects.filter(
                    ~Q(_players__user=self.request.user)
                ),
                'user_games': models.Game.objects.filter(
                    _players__user=self.request.user
                ),
            }
        else:
            context = {'not_user_games': models.Game.objects.all()}

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

    @temporally(Card.Text, str_method='classic')
    def get(self, request: WSGIRequest, pk: int) -> HttpResponse:
        """handling GET request"""

        game: models.Game = get_object_or_404(models.Game, pk=pk)
        context = {'game': game}

        try:
            game.continue_processing()
        except RequirementError as e:
            logger.info(f'Requirement: {e}. Do nothing.')
            context['form'] = PlayerBetForm()
            context['form'].action_url = f'/games/{pk}/bet/'
            # context['form'].action_url = reverse(MakePlayerBetView.as_view(), kwargs={'pk': pk})

        try:
            context['player'] = request.user.players.get(game=game)
            context['other_players'] = game.players.filter(~Q(user=request.user))
        except models.Player.DoesNotExist:
            # monitoring mode (user are not playing at this game but watching)
            # return self.get_monitoring_mode(...)
            raise NotImplementedError('monitoring mode is not implemented yet')
        except models.Player.MultipleObjectsReturned:
            raise RuntimeError(
                'User can play in game only by one player.'
                'Something wrong with Player model constraints'
            )
        except AttributeError:
            # for non authenticated user
            # 'AnonymousUser' object has no attribute 'players'
            # monitoring mode (user are not playing at this game but watching)
            raise NotImplementedError('monitoring mode is not implemented yet')

        pluser_serializer = PlayerSerializer(request.user.players.get(game=game))
        other_players_serializer = PlayerSerializer(
            game.players.filter(~Q(user=request.user)), many=True
        )
        games_serializer = GameSerializer(instance=game, context={'request': request})

        _game=dict(games_serializer.data),
        _pluser=dict(pluser_serializer.data),
        #_other=dict(other_players_serializer.data),

        log = {"game": _game, 'pluser': _pluser}
        logger.info(f'GAME INFO: \n {pformat(log)}')

        return render(request, self.template, context)

    def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        player: models.Player = request.user.players.get(game=game)

        try:
            game.continue_processing()
        except RequirementError as e:
            logger.info(f'Requirement: {e}. Try to satisfy it. ')

            if e.requirement == models.HostApprovedGameStart:
                if player.host:
                    e.requirement.satisfy()
                    # try:
                    #     game.continue_processing()
                    # except RequirementError as second_e:
                    #     if e == second_e:
                    #         logger.error(f'The same RequirementError was catched. Do nothing. ')
                else:
                    logger.warning(f'No satisfaction was found. ')

            # elif other requirements ...
            #   ...
            else:
                logger.warning(f'No satisfaction was found. ')

        return redirect(self.namespace_name, pk=pk)


class MakePlayerBetView(views.View):
    name = 'bet'
    full_name = app_name + ':' + name

    def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        player: models.Player = request.user.players.get(game=game)

        form = PlayerBetForm(data=request.POST, instance=player.bet)

        if form.is_valid():
            form.save()
            logger.info('form saved')
            # bet: PlayerBet = form.save(commit=False)
            # bet.player = player
            # bet.save()

        return redirect(GameView.namespace_name, pk=pk)
