from __future__ import annotations
from io import StringIO
from itertools import chain
import logging
import re

import pytest
from core.utils import TemporaryContext
from core.utils import StrColors, change_loggers_level, init_logger
from rest_framework import status
from django.core.management import call_command
from rest_framework.test import APIClient
from core.utils.types import JSON
from django.http import HttpResponsePermanentRedirect
from games.configurations.configurations import CONFIG_SCHEMAS
from games.models.player import Player, PlayerPreform
from games.services import stages
from games.services.cards import Card

from games.services import actions
from games.services.processors import AutoProcessor, BaseProcessor
from tests.base import BaseGameProperties, APIGameProperties
from games.services.combos import Combo
from users.models import User


logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures('someuser', 'setup_game', 'setup_participant', 'setup_urls', 'setup_clients',)
class TestGameAPI(APIGameProperties):

    ####################################################################################
    # Test Game Endponts
    ####################################################################################

    def test_games_endpoint_create_game(self):
        # those fields expected to be ignored:
        read_only_fields = {'bank': 123, 'begins': True, 'rounds_counter': 999}
        data = {'config_name': 'bizarre'}
        data.update(read_only_fields)
        self.assert_response(
            '[1] create game', 'vybornyy', 'POST', 'games', expected_status=status.HTTP_201_CREATED, **data
        )
        assert self.response_data['config'] == CONFIG_SCHEMAS['bizarre']
        assert self.response_data['bank'] == 0
        assert self.response_data['begins'] == False
        assert self.response_data['rounds_counter'] == 1

        # assert that user join that game (as a host)
        assert self.response_data['players'][0] == 'vybornyy'

    @pytest.mark.skip('not implemented yet')
    def test_games_endpoint_delete_game(self):
        ...

    def test_games_endpoint_list_and_retrieve(self):
        AutoProcessor(self.game, stop_after_stage=stages.FlopStage_1).run()
        self.assert_response('[1] list of games', 'vybornyy', 'GET', 'games')
        self.assert_response('[2] game detail after flop ', 'vybornyy', 'GET', 'game_detail')

        test = '[3] assert game table string using `classic` method of representation. '
        logger.info(StrColors.purple(test))
        table_string = ' '.join([card['string'] for card in self.response_data['table']])
        with TemporaryContext(Card.Text, str_method='classic'):
            assert table_string == str(self.game.table)

    def test_games_endpoint_stage_property(self):
        AutoProcessor(self.game, stop_after_stage=stages.FlopStage_1).run()
        self.assert_response('[1] game detail after flop', 'vybornyy', 'GET', 'game_detail')
        assert self.response_data['stage']['name']
        assert self.response_data['stage']['performer']
        assert self.response_data['stage']['status']

    ####################################################################################
    # Test Game Players Endpont
    ####################################################################################

    def test_players_endpoint_list_retrive_me_other(self):
        AutoProcessor(self.game, stop_after_stage=stages.DealCardsStage_1).run()

        test = '[1] GET by user that playing in that game'
        logger.info(StrColors.purple(test))

        self.assert_response('', 'vybornyy', 'GET', 'players')
        assert len(self.response_data) == len(self.players)

        self.assert_response('', 'vybornyy', 'GET', 'players/me')
        # assert only one player
        assert not isinstance(self.response_data, list)
        assert self.response_data['user'] == str(self.players_list[0].user)

        self.assert_response('', 'vybornyy', 'GET', 'players/other')
        # assert all players except me player
        assert len(self.response_data) == len(self.players) - 1
        assert self.response_data[0]['user'] == str(self.players_list[1].user)
        assert self.response_data[1]['user'] == str(self.players_list[2].user)

        test = '[2] GET by user that NOT playing in that game'
        logger.info(StrColors.purple(test))

        self.assert_response('', 'someuser', 'GET', 'players')
        self.assert_response('', 'someuser', 'GET', 'players/me', status.HTTP_403_FORBIDDEN)
        self.assert_response('', 'someuser', 'GET', 'players/other', status.HTTP_403_FORBIDDEN)

        test = '[3] GET by anonymous user | Allowed to get all players but forbidden to get "/me" or "/other"'
        logger.info(StrColors.purple(test))

        self.assert_response('', 'anonymous', 'GET', 'players')
        self.assert_response('', 'anonymous', 'GET', 'players/me', status.HTTP_401_UNAUTHORIZED)
        self.assert_response('', 'anonymous', 'GET', 'players/other', status.HTTP_401_UNAUTHORIZED)

    def test_players_endpoint_create(self):

        # those fields expected to be ignored:
        read_only_fields = {'bets': [10, 20, 30], 'is_dealer': True, 'position': 123}
        data = {'user': self.participant}
        data.update(read_only_fields)
        self.assert_response('', 'vybornyy', 'POST', 'players', status.HTTP_201_CREATED, **data)

        assert not PlayerPreform.objects.exists()
        assert self.game.players_manager.count() == len(self.players) + 1
        assert self.response_data['bets'] == []
        assert self.response_data['is_dealer'] is not True
        assert self.response_data['position'] != 123

    def test_players_endpoint_create_failed(self):
        initial_players_amount = len(self.players)

        data = {'user': self.participant}
        self.assert_response('[1] unauthorized', 'anonymous', 'POST', 'players', status.HTTP_401_UNAUTHORIZED, **data)
        self.assert_response('[2] not host', 'simusik', 'POST', 'players', status.HTTP_403_FORBIDDEN, **data)

        data['user'] = User.objects.get(username='someuser')
        self.assert_response(
            '[3] user not at PlayerPreform', 'vybornyy', 'POST', 'players',
            status.HTTP_404_NOT_FOUND, **data  # fmt: skip
        )
        error = r'.*User is not waiting to take part in game.*'
        assert re.match(error, self.response_data['detail'])
        assert self.game.players_manager.count() == initial_players_amount

        actions.StartAction.run(self.game)
        data['user'] = self.participant
        self.assert_response(
            '[4] create user not at Setup Stage', 'vybornyy', 'POST', 'players',
            status.HTTP_409_CONFLICT, **data  # fmt: skip
        )
        assert self.response_data['code'] == 'invalid_stage'
        assert self.game.players_manager.count() == initial_players_amount

    def test_players_endpoint_delete(self):
        self.assert_response(
            'success: host delete barticheg at beginings',
            'vybornyy',
            'DELETE',
            'players/barticheg',
            status.HTTP_204_NO_CONTENT,
        )
        self.assert_response('host delete himself', 'vybornyy', 'DELETE', 'players/vybornyy', status.HTTP_403_FORBIDDEN)

        actions.StartAction.run(self.game)

        self.assert_response(
            'host delete other player not at SetupStage',
            'vybornyy',
            'DELETE',
            'players/simusik',
            status.HTTP_409_CONFLICT,
        )
        self.assert_response(
            'success: delete himself', 'simusik', 'DELETE', 'players/simusik', status.HTTP_204_NO_CONTENT
        )

        test = 'all players except host came out | assert game proceed to final stage'
        logger.info(StrColors.purple(test))
        assert self.game.stage == stages.TearDownStage

    def test_players_endpoint_delete_after_bet_placed(self):
        game = self.game
        bet = actions.PlaceBet.prototype(
            game,
            self.users['simusik'],
            125,
            stages.BiddingsStage_2,
        )
        AutoProcessor(game, with_actions=[bet]).run()

        test = 'came out after bet placed | assert game take it to bank'
        logger.info(StrColors.purple(test))
        bank_before_action = self.game.bank
        self.assert_response('', 'simusik', 'DELETE', 'players/simusik', status.HTTP_204_NO_CONTENT)
        assert self.game.bank == bank_before_action + bet.action_values

        self.make_log()

    def test_players_endpoint_serializer_class(self):
        actions.StartAction.run(self.game)

        # cards hidden for others:
        self.assert_response('', 'vybornyy', 'GET', 'players')
        assert not any([any(player['hand']) for player in self.response_data])
        self.assert_response('', 'vybornyy', 'GET', 'players/me')
        assert all(self.response_data['hand'])
        self.assert_response('', 'vybornyy', 'GET', 'players/vybornyy')
        assert all(self.response_data['hand'])
        self.assert_response('', 'vybornyy', 'GET', 'players/other')
        assert not any([any(player['hand']) for player in self.response_data])

        # all cards not hidden at final stages:
        AutoProcessor(self.game, stop_before_stage=stages.TearDownStage).run()
        self.assert_response('', 'vybornyy', 'GET', 'players')
        assert all([all(player['hand']) for player in self.response_data])

    def test_players_endpoint_bets_fields(self):
        AutoProcessor(self.game, stop_before_stage=stages.BiddingsStage_1).run()
        self.assert_response('', 'vybornyy', 'GET', 'players')

        assert [p['bet_total'] for p in self.response_data] == [0, 5, 10]
        assert [bool(p['bets']) for p in self.response_data] == [False, True, True]
        assert [p['bets'] for p in self.response_data] == [[], [5], [10]]

    ####################################################################################
    # Test Game Actions Endponts
    ####################################################################################

    @property
    def possible_actions(self):
        return {action['name']: action for action in self.response_data}

    @property
    def possible_actions_names(self):
        return [action['name'] for action in self.response_data]

    @pytest.mark.skip('[TODO] need to refactor')
    def test_actions_endpoint_list(self):
        """test list method: get all avaliable actions"""
        self.assert_response(
            '[1] get all actions by host | assert start is avaliable',
            'vybornyy',
            'GET',
            'actions',
        )
        assert self.possible_actions_names == ['start']
        assert self.response_data[0]['url'] == self.urls['start']

        actions.StartAction.run(self.game)
        self.assert_response(
            '[2] get all actions by performer | ensure that `pass` is not avaliable',
            self.game.stage.performer.user,
            'GET',
            'actions',
        )
        assert self.possible_actions_names == ['blind']
        self.assert_response(
            '[3] get all actions by not performer | ensure that no actions provided',
            'vybornyy',
            'GET',
            'actions',
        )
        assert self.possible_actions_names == []

        actions.PlaceBlind.run(self.game)
        actions.PlaceBlind.run(self.game)
        self.assert_response(
            '[3] get all actions by performer on BiddingsStage_1',
            self.game.stage.performer.user,
            'GET',
            'actions',
        )
        assert self.possible_actions_names == ['bet', 'reply', 'vabank', 'pass']
        assert set(self.response_data[0]['values']) == {'min', 'max', 'step'}

    def test_actions_endpoint_error_response(self):
        AutoProcessor(self.game, stop_after_stage=stages.FlopStage_1).run()
        for invalid_bet in [17, -20, 10000]:
            self.assert_response(
                'place invalid bet value -> validation error',
                'simusik',
                'POST',
                'bet',
                status.HTTP_400_BAD_REQUEST,
                value=invalid_bet,
            )
            self.make_log()

        valid_bet = 10
        self.assert_response(
            'place bet action is not allowed for current game state -> conflict state error',
            'vybornyy',
            'POST',
            'bet',
            status.HTTP_409_CONFLICT,
            value=valid_bet,
        )
        self.make_log()


    def test_actions_endpoint_blind_bet_reply_check_vabank_pass(self, setup_users_banks: list[int]):
        self.assert_response('[1] vybornyy make avaliable action', 'vybornyy', 'POST', 'start')

        self.assert_response('', 'simusik', 'POST', 'blind')    # 5$
        self.assert_response('', 'barticheg', 'POST', 'blind')  # 10$

        # first biddings stage:
        bet = 20
        self.assert_response('act valid value', 'vybornyy', 'POST', 'bet', value=bet) # 20$
        self.assert_response('', 'simusik', 'POST', 'reply')    # 15$
        self.assert_response('', 'barticheg', 'POST', 'pass')

        # next biddings stage:
        self.assert_response('', 'simusik', 'POST', 'check')
        self.assert_response('', 'vybornyy', 'POST', 'vabank') # 990$
        self.assert_response('', 'simusik', 'POST', 'pass')

        test = '[2] check that winner got his benefit because all passed'
        logger.info(StrColors.purple(test))

        # benefit = big blind placed by simusik + bet placed by vybornyy
        benefit = bet + self.game.config.big_blind
        winner_bank = self.users['vybornyy'].profile.bank
        assert winner_bank == self.initial_users_bank['vybornyy'] + benefit

    def test_actions_endpoint_force_continue(self):
        self.assert_response('', 'vybornyy', 'POST', 'forceContinue') # start
        self.assert_response('', 'vybornyy', 'POST', 'forceContinue') # blind
        self.assert_response('', 'vybornyy', 'POST', 'forceContinue') # blind
        self.assert_response('', 'vybornyy', 'POST', 'forceContinue') # reply
        self.assert_response('', 'vybornyy', 'POST', 'forceContinue') # reply

        assert self.game.stage == stages.BiddingsStage_2



    ####################################################################################
    # Test playerPreform Endpont
    ####################################################################################

    def test_player_preform_endpoint(self):
        # list
        self.assert_response('', 'anonymous', 'GET', 'playersPreform', status.HTTP_401_UNAUTHORIZED)
        self.assert_response('', 'someuser', 'GET', 'playersPreform')
        self.assert_response('', 'participant', 'GET', 'playersPreform')
        self.assert_response('', 'vybornyy', 'GET', 'playersPreform')

        # retrieve
        ...

        # create
        self.assert_response('', 'someuser', 'POST', 'playersPreform', status.HTTP_201_CREATED)
        self.assert_response('', 'participant', 'POST', 'playersPreform', status.HTTP_400_BAD_REQUEST)
        self.assert_response('', 'vybornyy', 'POST', 'playersPreform', status.HTTP_403_FORBIDDEN)



@pytest.mark.django_db
#@pytest.mark.usefixtures()
class TestForceContinueAction(APIGameProperties):
    def test_actions_endpoint_force_continue_with_another_data(self, apply_default_data, apply_game, setup_urls, setup_clients):
        change_loggers_level(logging.ERROR)
        for i in range(200):
            self.assert_response('', 'simusik', 'POST', 'forceContinue')


