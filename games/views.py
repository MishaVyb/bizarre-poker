"""

developing:
[ ] apply @decorators.login_required

"""





from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django import views
from django.views.generic.list import ListView
from django.core.handlers.wsgi import WSGIRequest
from core.functools.decorators import temporary_globals
from django.contrib.auth import decorators, get_user_model
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from games import models
from games.backends.cards import Card, JokerCard
from poker import settings

User = get_user_model()
app_name = 'games'

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
                    ~Q(players__user=self.request.user)
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
    name = 'game'
    namespace_name = app_name + ':' + name
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

        try:
            context['player'] = request.user.players.get(game=game)
            context['other_players'] = game.players.filter(~Q(user=request.user))
        except models.Player.DoesNotExist:
            # monitoring mode (user are not playing at this game)
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
            return redirect(settings.LOGIN_URL)

        return render(request, self.template, context)

    def post(self, request: WSGIRequest, pk: int) -> HttpResponse:
        # next:
        game: models.Game = get_object_or_404(models.Game, pk=pk)

        try:
            next(game.process)
        except ObjectDoesNotExist:
            models.GameProcess.objects.create(game=game, status='new process')
            print('new process')
        except StopIteration:
            game.process.delete()
            models.GameProcess.objects.create(game=game, status='new process after del')
            print('new process after del')

        return redirect(self.namespace_name, pk=pk)