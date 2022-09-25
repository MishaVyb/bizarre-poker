from __future__ import annotations
from copy import copy

import re
from pprint import pformat
from typing import Iterable, Literal, OrderedDict

import pytest
from core.functools.utils import StrColors, init_logger
from rest_framework import status

from rest_framework.test import APIClient
from core.types import JSON
from django.http import HttpResponsePermanentRedirect
from tests.base import BaseGameProperties, APIGameProperties
from games.services.combos import Combo
from games.services.auto import autoplay_game

logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures(
    'setup_clients',
    'setup_game',
    'setup_urls',
)
class TestGameAPI(APIGameProperties):
    urls = {
        'test_action': '/api/v1/games/test_action/',
        # create game, delete game
        'games': '/api/v1/games/',  # test is done
        # game info
        'game_detail': '/api/v1/games/{game_pk}/',  # test is done
        # get: all players at game
        # create: join game
        # delete: leave game
        'players': '/api/v1/games/{game_pk}/players/',  # test is done
        'players/me': '/api/v1/games/{game_pk}/players/me/',  # test is done
        'players/other': '/api/v1/games/{game_pk}/players/other/',  # test is done
        'players/active': '/api/v1/games/{game_pk}/players/active/',
        # get: all valid and invalid actions
        'actions': '/api/v1/games/{game_pk}/actions/',
        # make action
        'start': '/api/v1/games/{game_pk}/actions/start/',  # post
        'pass': '/api/v1/games/{game_pk}/actions/pass/',  # post
        'blind': '/api/v1/games/{game_pk}/actions/blind/',  # post
        'bet': '/api/v1/games/{game_pk}/actions/bet/',  # post
        'check': '/api/v1/games/{game_pk}/actions/check/',  # post
        'reply': '/api/v1/games/{game_pk}/actions/reply/',  # post
        'vabank': '/api/v1/games/{game_pk}/actions/vabank/',  # post
    }

    @property
    def avaliable_action_names(self):
        return [action['name'] for action in self.response_data['avaliable']]

    def test_games_endpoint(self):
        self.assert_response(
            '[1] create game',
            'vybornyy',
            'POST',
            'games',
            expected_status=status.HTTP_201_CREATED,
        )
        # assert that user join that game as host
        assert '(0) vybornyy(h)(d)' in self.response_data['players'][0]

        autoplay_game(self.game, stop_after_stage='FlopStage-1')

        self.assert_response(
            '[2] game detail after flop | assert that deck is hiden',
            'vybornyy',
            'GET',
            'game_detail',
        )
        assert self.response_data['table'] == str(self.game.table)
        assert self.response_data['deck'] == self.game.deck.hiden()

        self.assert_response(
            '[3] list of games',
            'vybornyy',
            'GET',
            'game_detail',
        )

    def test_players_endpoint(self):
        autoplay_game(self.game, stop_after_stage='DealCardsStage')

        self.assert_response(
            '[1] get players',
            'vybornyy',
            'GET',
            'players',
        )
        assert self.response_data[0]['hand'] == str(self.players_list[0].hand)
        assert self.response_data[1]['hand'] == self.players_list[1].hand.hiden()
        assert self.response_data[2]['hand'] == self.players_list[2].hand.hiden()

        self.assert_response(
            '[2] get players/me',
            'vybornyy',
            'GET',
            'players/me',
        )
        assert not isinstance(self.response_data, list)  # not a list - only one player
        assert self.response_data['hand'] == str(self.players_list[0].hand)

        self.assert_response(
            '[2] get players/other',
            'vybornyy',
            'GET',
            'players/other',
        )
        assert len(self.response_data) == 2
        assert self.response_data[0]['hand'] == self.players_list[1].hand.hiden()
        assert self.response_data[1]['hand'] == self.players_list[2].hand.hiden()
        assert self.response_data[0]['user'] == str(self.players_list[1].user)
        assert self.response_data[1]['user'] == str(self.players_list[2].user)

    def test_actions_endpoint(self, setup_users_banks):
        self.assert_response(
            '[1] get all actions by host | assert start is avaliable',
            'vybornyy',
            'GET',
            'actions',
        )
        assert self.avaliable_action_names == ['start']
        assert self.response_data['avaliable'][0]['url'] == self.urls['start']

        self.assert_response(
            '[2] vybornyy make avaliable action', 'vybornyy', 'POST', 'start'
        )
        self.assert_response(
            '[3] get all actions by small blind maker', 'simusik', 'GET', 'actions'
        )
        assert self.avaliable_action_names == ['blind', 'pass']
        # pass action has no value:
        assert self.response_data['avaliable'][1].get('value') is None

        self.assert_response('[4] act invalid action', 'simusik', 'POST', 'start')
        expected = r'Game has another current stage'
        assert expected in self.response_data['act_error']

        self.assert_response('[5] act valid', 'simusik', 'POST', 'blind')
        self.assert_response('[6] act valid', 'barticheg', 'POST', 'pass')
        self.assert_response(
            '[7] act invalid value', 'vybornyy', 'POST', 'bet', {'value': -20}
        )
        expected = r'Condition value_in_necessary_range are not satisfied'
        assert expected in self.response_data['act_error']

        self.assert_response('', 'vybornyy', 'POST', 'bet', {'value': 1000000})
        expected = r'Condition value_in_necessary_range are not satisfied'
        assert expected in self.response_data['act_error']

        self.assert_response('', 'vybornyy', 'POST', 'bet', {'value': 17})
        expected = r'It is not multiples of small blind'
        assert expected in self.response_data['act_error']

        valid_bet = 20
        self.assert_response(
            '[8] act valid value', 'vybornyy', 'POST', 'bet', {'value': valid_bet}
        )
        self.assert_response('[9]', 'simusik', 'POST', 'reply')
        self.assert_response('[10]', 'vybornyy', 'POST', 'check')
        self.assert_response('[11]', 'simusik', 'POST', 'vabank')
        self.assert_response('[12]', 'vybornyy', 'POST', 'pass')

        # winner got his benefit
        assert self.users_list[1].profile.bank == setup_users_banks[1] + valid_bet

        # game waiting for new game round begins
        assert self.response_data['stage']['name'] == 'SetupStage'
        assert self.response_data['stage']['performer'] == '(2) vybornyy(h)'

        # self.assert_response('', 'simusik', 'GET', 'game_detail')
        # self.make_log()

    def test_players_endpoint_bet_total(self):
        autoplay_game(self.game, stop_before_stage='BiddingsStage-1')
        # autoplay_game(self.game, stop_after_actions_amount=1)

        self.assert_response('', 'vybornyy', 'GET', 'players')
        assert [p['bet_total'] for p in self.response_data] == [0, 5, 10]
        assert [p['bets'] for p in self.response_data] == [False, True, True]

        self.assert_response('', 'vybornyy', 'GET', 'players/me')
        assert self.response_data['bet_total'] == 0
        assert self.response_data['bets'] == False

        self.assert_response('', 'vybornyy', 'GET', 'players/other')
        assert [p['bet_total'] for p in self.response_data] == [5, 10]
        assert [p['bets'] for p in self.response_data] == [True, True]

        autoplay_game(self.game, stop_after_actions_amount=1)

    def test_game_api(self):

        # test: if host leave the game
        ...

        # test: if host join game again
        ...

        # test: if no player want look at game deteail
        ...

        # test: start with no other players
        ...

        # test other players join game
