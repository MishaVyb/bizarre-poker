from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django import views
from django.views.generic.list import ListView
from django.core.handlers.wsgi import WSGIRequest
from core.functools.decorators import temporary_globals
from django.contrib.auth import get_user_model

from games import models
from games.backends.cards import Card, JokerCard

User = get_user_model()

class IndexView(views.View):
    template = 'games/index.html'
    title = ''

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """define a request type and calling appropriate class metodh"""
        return super().dispatch(request, *args, **kwargs)

    @temporary_globals(
        Card__STR_METHOD=Card.Text.repr_as_emoji,
        JokerCard__STR_METHOD=JokerCard.Text.repr_as_emoji,
    )
    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponse:
        """handling GET request"""
        if request.user.is_authenticated:
            context = {
                'not_user_games': models.Game.objects.filter(
                    ~models.Q(players__user=self.request.user)
                ),
                'user_games': models.Game.objects.filter(
                    players__user=self.request.user
                ),
            }
        else:
            context = {
                'not_user_games': models.Game.objects.all()
            }

        return render(request, self.template, context)


class UserGamesListView(ListView):
    context_object_name = 'games'

    def get_queryset(self):
        return models.Game.objects.filter(players__user=self.request.user)

class GameView(views.View):
    template = 'games/game.html'
    title = ''

    @temporary_globals(
        Card__STR_METHOD=Card.Text.repr_as_emoji,
        JokerCard__STR_METHOD=JokerCard.Text.repr_as_emoji,
    )
    def get(self, request: WSGIRequest, pk: int) -> HttpResponse:
        """handling GET request"""
        game: models.Game = get_object_or_404(models.Game, pk=pk)
        context = {'game': game}

        if request.user.is_authenticated:
            try:
                context['pluser'] = request.user.players.get(game=game)
            except models.Player.DoesNotExist:
                # okey, user are not playing at this game
                pass
            except models.Player.MultipleObjectsReturned:
                raise RuntimeError(
                    'User can play in game only by one player.'
                    'Something wrong with Player model constraints'
                    )



        return render(request, self.template, context)
