import logging
from math import gamma
from multiprocessing import managers
from typing import Any
from django.db import IntegrityError

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser

from core.functools.utils import StrColors, isinstance_items
from games.backends.cards import CardList, Stacks
from games.backends.combos import CLASSIC_COMBOS
from games.models import Game, Player
from games.models.game import GameManager
from games.models.player import (
    PlayerBet,
    PlayerBetManager,
    PlayerBetQuerySet,
    PlayerManager,
    PlayerQuerySet,
)
from ..services import stages, actions

from users.models import User
from core.functools.utils import init_logger
from django.core.exceptions import ValidationError

logger = init_logger(__name__, logging.INFO)


@pytest.mark.django_db
@pytest.mark.usefixtures('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
class TestServices:
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    # input_users_banks = (2000, 3000, 4000, 5000)
    game_pk: int = 0
    input_users_bank: dict = {}

    def set_users_bank_values(self):
        for i, u in enumerate(User.objects.all()):
            u.profile.bank = (i + 1) * 1000 + (i + 1) * 10
            u.profile.save()
            self.input_users_bank[u.username] = u.profile.bank

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self.game_pk)

    @property
    def players(self) -> dict[str, Player]:
        return {p.user.username: p for p in self.game.players}

    def start_game(self):
        print('\n')
        logger.info(StrColors.header('[0] create game with players and start it'))
        self.set_users_bank_values()
        self.game_pk = Game(players=self.users.values(), commit=True).pk
        actions.StartAction(self.game, self.users['vybornyy'])

    def test_place_blinds_action(self):
        self.start_game()
        p = list(self.players.values())
        test = '[1] test there are no beds at beginings'
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[2] PlaceBlind by simusik | test beds values'
        logger.info(StrColors.header(test))
        actions.PlaceBlind(self.game, self.users['simusik'])
        assert [0, 5, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[3] PlaceBlind by vybornyy | test raises'
        logger.info(StrColors.header(test))
        match = (
            r'Acting PlaceBlind failed. '
            r'Game waiting for act from another player: .* barticheg'
        )
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBlind(self.game, self.users['vybornyy'])

        test = '[4] PlaceBlind by barticheg | test bet values and current stage'
        logger.info(StrColors.header(test))
        actions.PlaceBlind(self.game, self.users['barticheg'])
        assert [0, 5, 10, 0] == [p.bet_total for p in self.game.players]
        assert self.game.stage.__class__.__name__ == 'BiddingsStage-1'

        test = '[5] PlaceBlind by vybornyy | test raises when game has another stage'
        logger.info(StrColors.header(test))
        match = (
            r'Acting PlaceBlind failed. '
            r'Game has another current stage: BiddingsStage-1'
        )
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBlind(self.game, self.users['vybornyy'])

    def test_invalid_bet_values(self):
        self.start_game()

        test = (
            '[2] PlaceBet by simusik with invalid value=10, but expectd=5 (small blind)'
        )
        logger.info(StrColors.header(test))
        match = (
            r'Acting PlaceBet failed. '
            r'Game has another current stage: PlacingBlindsStage'
        )
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['simusik'], value=10)
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[3] PlaceBlinds by simusik and barticheg to go ahead'
        logger.info(StrColors.header(test))
        actions.PlaceBlind(self.game, self.users['simusik'])
        actions.PlaceBlind(self.game, self.users['barticheg'])

        test = '[4] PlaceBet by arthur_morgan with invalid values'
        logger.info(StrColors.header(test))

        condition_name = 'bet_equal_or_more_then_others'
        match = rf'Condition {condition_name} for acting PlaceBet are not satisfied'
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=0)

        condition_name = 'player_has_enough_money'
        match = rf'Condition {condition_name} for acting PlaceBet are not satisfied'
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=10000)

        self.users['vybornyy'].profile.update(bank=400)
        condition_name = 'bet_is_not_more_then_others_banks'
        match = rf'Condition {condition_name} for acting PlaceBet are not satisfied'
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=500)

        condition_name = 'value_multiples_of_small_blind'
        match = rf'Condition {condition_name} for acting PlaceBet are not satisfied'
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=13)

    def test_start_action(self):
        print('\n')
        logger.info(StrColors.header('[0] create game with players'))
        self.game_pk = Game(players=self.users.values(), commit=True).pk

        # test begins flag
        assert self.game.begins is False

        # [1] test game stage before beginings
        logger.info(StrColors.header('[1] test game stage before beginings'))

        # test who is performer, by default it should be host player
        # access through model field
        assert self.game.stage.performer == self.players['vybornyy']
        # access through dinamic property "stage"
        assert self.game.stage.performer == self.players['vybornyy']
        # test nessacery action
        assert self.game.stage.necessary_action == 'StartAction'

        # [2] test game stages processing no failers
        logger.info(StrColors.header('[2] test game stages processing no failers'))
        stages.GAME_STAGES_LIST.continue_processing(self.game)

        # [3] test NOT host press "start"
        logger.info(StrColors.header('[3] test NOT host press "start'))
        match = (
            r'Acting StartAction failed. '
            r'Game waiting for act from another player: .* vybornyy'
        )
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.StartAction(self.game, self.users['simusik'])

        # [4]
        logger.info(StrColors.header('[4] test host "start"'))
        actions.StartAction(self.game, self.users['vybornyy'])

    def test_place_bet_all_actions(self):
        self.start_game()

        ## добавим еще одного плеера и сразу же им пасанем, проверим что все работает

        # [4.2]
        logger.info(StrColors.header('[4.2] place blinds'))
        actions.PlaceBlind(self.game, self.users['simusik'])
        actions.PlaceBlind(self.game, self.users['barticheg'])

        # [5] test place bet stage
        logger.info(StrColors.header('[5] test place bet'))
        assert self.game.stage.performer == self.players['arthur_morgan']
        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-1'
        assert self.game.stage.necessary_action == 'PlaceBet'
        assert [0, 5, 10, 0] == [p.bet_total for p in self.game.players]

        # [6] test trying another player place bet
        logger.info(StrColors.header('[6] test trying another player place bet'))
        match = (
            r'Acting PlaceBet failed. '
            r'Game waiting for act from another player: .* arthur_morgan'
        )
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBet(self.game, self.users['simusik'], 25)

        # [7]
        logger.info(StrColors.header('[7] test 2 remainig players place a valid bet.'))
        actions.PlaceBet(self.game, self.users['arthur_morgan'], 25)
        actions.PlaceBet(self.game, self.users['vybornyy'], 25)
        assert [25, 5, 10, 25] == [p.bet_total for p in self.game.players]

        # [8]
        test = '[8] next biddings circle. Match bet values. Game processing ahead to next BiddingStage'
        logger.info(StrColors.header(test))
        p = [p for p in self.game.players]
        b = [str(p.bet_total) for p in self.game.players]
        actions.PlaceBet(self.game, self.users['simusik'], 20)
        actions.PlaceBet(self.game, self.users['barticheg'], 15)

        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-2'
        # assert there are no beds yet
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]
        # check that player after dealer is a first bet maker
        assert self.game.stage.performer == self.players['simusik']

        # [9]
        test = '[9] simusik say "check" (Zero bet will be placed)'
        logger.info(StrColors.header(test))
        actions.PlaceBetCheck(self.game, self.users['simusik'])

        # [10]
        test = '[10] barticheg say "VaBank"'
        logger.info(StrColors.header(test))
        actions.PlaceBetVaBank(self.game, self.users['barticheg'])
        expected = self.input_users_bank['vybornyy'] - 25
        assert expected == self.players['barticheg'].bet_total

        # [11]
        test = (
            '[11] arthur_morgan trying say "check" when there are other bet were placed'
        )
        logger.info(StrColors.header(test))
        condition_name = 'bet_equal_or_more_then_others'
        match = rf'Condition {condition_name} for acting PlaceBetCheck are not satisfied'
        with pytest.raises(actions.ActError, match=match) as exc_info:
            actions.PlaceBetCheck(self.game, self.users['arthur_morgan'])

        # [12]
        test = '[12] arthur_morgan say pass | test that he is out of game now'
        logger.info(StrColors.header(test))
        actions.PassAction(self.game, self.users['arthur_morgan'])
        assert self.players['arthur_morgan'].is_active == False
        assert self.game.stage.performer == self.players['vybornyy']


        # [13]
        test = '[13] vybornyy say pass'
        logger.info(StrColors.header(test))
        actions.PassAction(self.game, self.users['vybornyy'])
        expected = [self.players['simusik'], self.players['barticheg']]
        assert expected == list(self.game.players.active)

        # [14]
        test = '[14] simusik say reply | test game go ahead to next stage'
        logger.info(StrColors.header(test))
        actions.PlaceBetReply(self.game, self.users['simusik'])

        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-3'

        # [15]
        test = '[15] simusik and barticheg say check twice | test game go ahead to next stage'
        logger.info(StrColors.header(test))

        actions.PlaceBetCheck(self.game, self.users['simusik'])
        actions.PlaceBetCheck(self.game, self.users['barticheg'])
        b = [p.bet_total for p in self.game.players.active]
        bn = [p.bet_total_none for p in self.game.players.annotate_bet_total_with_none()]
        p = self.game.players.order_by_bet
        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-4(final)'



        actions.PlaceBetCheck(self.game, self.users['simusik'])
        actions.PlaceBetCheck(self.game, self.users['barticheg'])

    def test_necessary_action_values(self):
        self.start_game()

        test = '[1] test necessary_action_values'
        logger.info(StrColors.header(test))
        assert self.game.stage.get_necessary_action_values() == {'value': 5}

        test = '[2] go ahead...'
        logger.info(StrColors.header(test))
        actions.PlaceBlind(self.game, self.users_list[1])
        actions.PlaceBlind(self.game, self.users_list[2])

        assert self.game.stage.get_necessary_action_values() == {'max': 1010, 'min': 10}





########################################### move to another module ####################


from django.db import models


@pytest.mark.django_db
@pytest.mark.usefixtures('vybornyy', 'simusik', 'barticheg')
class TestModels:
    usernames = ('vybornyy', 'simusik', 'barticheg')
    game_pk: int = 0

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self.game_pk)

    @property
    def players(self) -> dict[str, Player]:
        return {p.user.username: p for p in self.game.players}

    def test_game_manager(self):
        assert isinstance(Game.objects, GameManager)

    def test_player_manager(self):
        assert isinstance(Player.objects, models.Manager)
        assert hasattr(Game, 'players'), 'players is a RelatedDescriprot class'
        assert not isinstance(Game.players, PlayerManager), (
            'There are no access to releted manager `players` through class, '
            'it`s allowed only for instances'
        )

        self.game_pk = Game(players=User.objects.all(), commit=True).pk
        for p in self.game.players:
            assert isinstance(p, Player)

        p = self.game.players.active[0]
        assert isinstance(p, Player)

        # crete another Game
        self.game_pk = Game(players=User.objects.all(), commit=True).pk

        # via class -- forbidden, becaues default manaeg is setted for `objects`
        with pytest.raises(
            AttributeError, match=r"'Manager' object has no attribute 'host'"
        ):
            Player.objects.host

        # via related instance -- okey
        assert self.game.players.host

        # player manager has custom query set for redefine some methods
        assert isinstance(self.game.players.all(), PlayerQuerySet)

    def test_players_ordering(self):
        self.game_pk = Game(players=User.objects.all(), commit=True).pk
        assert self.game.players.all()[0].user.username == 'vybornyy'
        assert self.game.players.all()[0].position == 0
        assert self.game.players.after_dealer[0].user.username == 'simusik'
        assert self.game.players.after_dealer[0].position == 1

    def test_players_attributes(self):
        self.game_pk = Game(players=User.objects.all(), commit=True).pk

        # dealer
        assert self.game.players[0].is_dealer
        assert not self.game.players[1].is_dealer
        assert [p.is_dealer for p in self.game.players] == [True, False, False]

        # other_players
        expected = [self.players['simusik'], self.players['barticheg']]
        assert list(self.game.players.dealer.other_players) == expected

    def test_player_bet(self):
        self.game_pk = Game(players=User.objects.all(), commit=True).pk
        self.players['simusik'].bets.create(value=15)
        self.players['simusik'].bets.create(value=25)
        self.players['barticheg'].bets.create(value=10)

        # bet total
        aggregated = self.game.players[1].bets.aggregate(total=models.Sum('value'))
        assert aggregated['total'] == 40
        assert self.game.players[1].bet_total == 40

        assert self.game.players[1].bet_total == 40  # via annotated field at player
        assert self.game.players[1].bets.total == 40  # via qs agregated property
        assert self.game.players.get(bet_total=40) == self.players['simusik']

        # none if player was not make a bet
        assert self.game.players[0].bet_total == 0
        assert self.game.players[0].bets.total == 0

        # узнаем кто не сделал ставку
        expected = [self.game.players[0]]
        assert list(self.game.players.without_bet) == expected

        # узнаем наиболшую ставку в игре
        max_bet = self.game.players.aggregate(models.Max('bet_total'))
        assert max_bet['bet_total__max'] == 40
        assert self.game.players.with_max_bet.bet_total == 40

        # bets equality
        assert self.game.players.check_bet_equality() == False
        self.players['barticheg'].bets.create(value=30)
        self.players['vybornyy'].bets.create(value=40)
        assert self.game.players.check_bet_equality() == True

        # if there are no bets at alll
        PlayerBet.objects.all().delete()
        assert self.game.players.check_bet_equality() == True

        # if there are only one bet
        self.players['simusik'].bets.create(value=15)
        assert self.game.players.check_bet_equality() == False

        # bet filter who has not max bet
        max_bet = self.game.players.with_max_bet.bet_total
        a = self.game.players.after_dealer
        b = [p.bet_total for p in self.game.players.after_dealer]
        q = self.game.players.after_dealer.filter(
            ~models.Q(bet_total=max_bet) | models.Q(bet_total=0)
        )
        assert q[0] == self.players['barticheg']
        assert q[1] == self.players['vybornyy']
