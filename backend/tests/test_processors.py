from pprint import pformat

import pytest
from core.functools.utils import StrColors, init_logger
from games.services import actions, stages
from games.services.combos import Combo

from games.services.processors import AutoProcessor
from users.models import User

from tests.base import BaseGameProperties
from tests.tools import param_kwargs_list

logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestGameProcessors(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    input_users_bank: dict[str, int]

    def test_base_processor(self):
        # self.game.processor.run()

        # actions.StartAction.run(self.game, self.users_list[0])
        # actions.PlaceBlind.run(self.game, self.users_list[1])
        # actions.PlaceBlind.run(self.game, self.users_list[2])

        # actions.PlaceBetReply.run(self.game, self.users_list[3])

        # AutoProcessor(self.game, stop_after_rounds_amount=1).run()
        # AutoProcessor(self.game, stop_after_actions_amount=3).run()
        game = self.game
        mega_bet = actions.PlaceBet.prototype(
            game, game.players[3], [125], stages.BiddingsStage_3
        )
        bet = actions.PlaceBet.prototype(game, game.players[0], [10])
        AutoProcessor(
            game,
            with_actions=[mega_bet, bet],
            # stop_after_action=mega_bet,
            stop_after_stage=stages.OpposingStage,
        ).run()

        # AutoProcessor(self.game, stop_after_stage=stages.OpposingStage).run()

        # logger.info(pformat(self.game.actions_history))


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestAuto(BaseGameProperties):
    input_users_bank: dict[str, int]

    def test_autoplay_game(self):
        AutoProcessor(self.game, stop_after_stage=stages.SetupStage).run()

        # stage iterated to next stage
        assert self.game.stage == stages.DealCardsStage_1

        # but next stage does not executed
        assert not self.game.table

        AutoProcessor(self.game, stop_before_stage=stages.BiddingsStage_4).run()
        assert self.game.stage == stages.BiddingsStage_4

    def test_autoplay_game_after_action(self):
        # [1] stop after action
        game = self.game
        start = actions.StartAction.prototype(game, game.players[0])
        AutoProcessor(self.game, stop_after_action=start).run()

        # game still at this stage
        assert self.game.stage == stages.SetupStage
        # but does not require any action from performer
        assert self.game.stage.performer is None

        # [2] stop before action
        bet = actions.PlaceBet.prototype(
            game, game.players[0], action_values=[self.game.config.big_blind]
        )
        AutoProcessor(game, stop_before_action=bet).run()

        # game still at this stage
        assert self.game.stage == stages.BiddingsStage_1
        # game still waiting him for act
        assert self.game.stage.performer == self.players_list[0]
        # and obvious he didn`t make a bet yet
        assert self.players_list[0].bet_total == 0

        # [3] stop before action
        bet = actions.PlaceBet.prototype(game, game.players[1], action_values=[0])
        AutoProcessor(game, stop_before_action=bet).run()

        # game at this stage
        assert self.game.stage == stages.BiddingsStage_2
        # game waiting him for act
        assert self.game.stage.performer == self.players_list[1]

    def test_autoplay_game_after_action_double_round(self):
        # for the 1st round vybornyy wan`t place a blind, but at the 2nd one will
        # bet = actions.PlaceBlind(self.game, self.users_list[0], act_immediately=False)

        game = self.game
        bet = actions.PlaceBlind.prototype(game, game.players[0])
        AutoProcessor(self.game, stop_before_action=bet).run()
        assert self.game.rounds_counter == 2  # second round has been begun
        assert self.game.stage == stages.PlacingBlindsStage

    def test_autoplay_game_after_action_raises(self):
        game = self.game
        bet = actions.PlaceBet.prototype(game, game.players[0], action_values=[12345])
        with pytest.raises(RuntimeError, match=r'Too many game round iterations'):
            AutoProcessor(self.game, stop_before_action=bet).run()

    def test_autoplay_game_stop_with_actions(self, setup_users_banks):
        bet_value = 100
        game = self.game
        bet = actions.PlaceBet.prototype(
            game,
            game.players[0],
            [bet_value],
            stages.BiddingsStage_2,
        )
        pass_ = actions.PassAction.prototype(
            game,
            game.players[1],
            suitable_stage_class=stages.BiddingsStage_2,
        )
        AutoProcessor(game, with_actions=[bet, pass_]).run()

        bet_total = self.game.config.big_blind + bet_value
        assert self.users_list[0].profile.bank == setup_users_banks[0] - bet_total
        assert next(self.game.players.passed) == self.players_list[1]

    def test_autoplay_game_actions_amount(self, setup_users_banks):
        AutoProcessor(self.game, stop_after_actions_amount=1).run()
        AutoProcessor(self.game, stop_after_actions_amount=1).run()
        AutoProcessor(self.game, stop_after_actions_amount=1).run()
        AutoProcessor(self.game, stop_after_actions_amount=1).run()
        assert [p.bet_total for p in self.players_list] == [10, 5, 10]
