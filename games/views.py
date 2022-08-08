"""

developing:
[ ] apply @decorators.login_required

"""
from typing import Any

from django import views
from django.contrib.auth import get_user_model
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.list import ListView

from core.functools.decorators import temporally
from games import models
from games.backends.cards import Card
from poker import settings
from users.models import User
from django.contrib.auth.models import AnonymousUser

app_name = 'games'


class IndexView(views.View):
    template = 'games/index.html'
    title = ''

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """define a request type and calling appropriate class metodh"""
        return super().dispatch(request, *args, **kwargs)

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
        assert isinstance(
            request.user, User | AnonymousUser
        ), 'requst should passed through user proxy middlware'
        
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        context = {'game': game}

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
            return redirect(settings.LOGIN_URL)

        return render(request, self.template, context)

    def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        try:
            next(game)
        except StopIteration:
            game.again()
            next(game)
        return redirect(self.namespace_name, pk=pk)
