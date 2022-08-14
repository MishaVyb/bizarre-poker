from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from django.urls import reverse
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from core.functools.decorators import temporally
from games.backends.cards import Card
from games.models import Game, Player

from django.db.models.query import QuerySet
from django.http.response import HttpResponse
from http import HTTPStatus
from django.db.models import Q

User = get_user_model()


@dataclass
class GameData:
    _game: Game
    _player: Player | None
    other_players: QuerySet[Player]
    url: str
    client: Client

    # game is changing at view, so we are making a query to get a relevant instances
    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self._game.pk)


    # the same for player
    @property
    def player(self) -> Player | None:
        try:
            return Player.objects.get(pk=self._game.pk)
        except Player.DoesNotExist:
            return None


@pytest.fixture
def game_with_bunch_of_players_data(client: Client, game_with_bunch_of_players: Game):

    game = game_with_bunch_of_players
    url = reverse('games:game', kwargs={'pk': game_with_bunch_of_players.pk})


    if not game.players:
        return GameData(game, None, game.players, url, client)
    else:
        player = game.players.first()
        other_players = game.players.filter(~Q(pk=player.pk))
        client.force_login(player.user)
        return GameData(game, player, other_players, url, client)



@pytest.mark.django_db
class TestGameView:
    data: GameData | None = None

    # def __call__(self, method: str, /, *args, raises=True, **kwargs):
    #     if not hasattr(self, method):
    #         if raises:
    #             raise AttributeError
    #         return None

    #     called: Callable = getattr(self, method)

    #     if not callable(called):
    #         if raises:
    #             raise TypeError
    #         return None

    #     return called(*args, **kwargs)

    def test_game_context(self, game_with_bunch_of_players_data: GameData):
        # game, player, other_players, url, client
        self.data = game_with_bunch_of_players_data
        data = self.data

        # GET REQUEST
        response: HttpResponse = data.client.get(data.url)

        if not data.player:
            assert response.status_code == HTTPStatus.FOUND, 'Client should be redirected if game has no players'
            return

        assert response.status_code == HTTPStatus.OK
        assert 'game' in response.context
        assert data.game == response.context['game']

        # POST REQUEST
        response = data.client.post(data.url, {})
        assert response.status_code == HTTPStatus.FOUND, 'Client should be redirected'
        assert response.url == data.url, 'to the same page for game demonstration'

        # make a redirection (get requst again)
        response = data.client.get(data.url)
        assert 'game' in response.context
        assert 'player' in response.context
        assert 'other_players' in response.context

        assert data.game == response.context['game']
        assert data.player == response.context['player']

        l1 = list(data.other_players)
        l2 = list(response.context['other_players'])
        assert data.other_players == response.context['other_players']

        #
        # INTEGRATE TEST BELOW !!!!


    # @pytest.skip('it is calling inside test_game_context')
    # @temporally(Card.Text, str_method='classic')
    # def test_deal_cards(self, data: GameData, response: HttpResponse):
    #     if not data.player:
    #         return

    #     decoded = response.content.decode()

    #     index_in = decoded.find('your hand')
    #     assert index_in > 0
    #     index_out = decoded.find('</p>', index_in)
    #     piece = decoded[index_in:index_out]
    #     required = str(data.player.hand)
    #     assert required in piece

    #     with temporally(Card.Text, str_method='emoji_shirt'):
    #         for other_player in data.other_players:
    #             index_in = decoded.find(other_player.user.get_username())
    #             assert index_in > 0
    #             index_out = decoded.find('</p>', index_in)
    #             piece = decoded[index_in:index_out]
    #             required = str(data.player.hand)
    #             assert required in piece
