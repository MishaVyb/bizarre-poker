from __future__ import annotations
import pytest

from games.services import actions, auto

from core.functools.utils import init_logger
from tests.base import BaseGameProperties
from games.services.configurations import DEFAULT

logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestAuto(BaseGameProperties):
    input_users_bank: dict[str, int]

    def test_autoplay_game(self):
        auto.autoplay_game(self.game, stop_after_stage='SetupStage')
        assert str(self.game.stage) == 'DealCardsStage'

        auto.autoplay_game(self.game, stop_before_stage='BiddingsStage-4(final)')
        assert str(self.game.stage) == 'BiddingsStage-4(final)'

    def test_autoplay_game_after_action(self):
        # [1] stop after action
        start = actions.StartAction.preform(self.users_list[0])
        auto.autoplay_game(self.game, stop_after_action_at_stage=start)

        # game still at this stage
        assert str(self.game.stage) == 'SetupStage'
        # but does not require any action from performer
        assert self.game.stage.performer is None

        # [2] stop before action
        bet = actions.PlaceBet.preform(self.users_list[0], value=DEFAULT.big_blind)
        auto.autoplay_game(self.game, stop_before_action_at_stage=bet)

        # game still at this stage
        assert str(self.game.stage) == 'BiddingsStage-1'
        # game still waiting him for act
        assert self.game.stage.performer == self.players_list[0]
        # and obvious he didn`t make a bet yet
        assert self.players_list[0].bet_total == 0

        # [3] stop before action
        bet = actions.PlaceBet.preform(self.users_list[1], value=0)
        auto.autoplay_game(self.game, stop_before_action_at_stage=bet)

        # game still at this stage
        assert str(self.game.stage) == 'BiddingsStage-2'
        # game still waiting him for act
        assert self.game.stage.performer == self.players_list[1]

    def test_autoplay_game_after_action_double_round(self):
        # for the 1st round vybornyy wan`t place a blind, but at the 2nd one will
        # bet = actions.PlaceBlind(self.game, self.users_list[0], act_immediately=False)

        bet: actions.ActionPreform[actions.PlaceBlind] = actions.PlaceBlind.preform(
            self.users_list[0], 'PlacingBlindsStage'
        )
        auto.autoplay_game(self.game, stop_before_action_at_stage=bet)

    def test_autoplay_game_after_action_raises(self):
        bet = actions.PlaceBet.preform(self.users_list[0], value=12345)
        with pytest.raises(RuntimeError, match=r'To many game round iterations'):
            auto.autoplay_game(self.game, stop_before_action_at_stage=bet)

    def test_autoplay_game_after_action_with_actions(self, setup_users_banks):
        bet_value = 100
        bet = actions.PlaceBet.preform(
            self.users_list[0], value=bet_value, stage='BiddingsStage-1'
        )
        pass_ = actions.PassAction.preform(self.users_list[1], stage='BiddingsStage-1')
        auto.autoplay_game(
            self.game, stop_after_stage='BiddingsStage-1', with_actions=[bet, pass_]
        )
        assert (
            self.users_list[0].profile.bank
            == self.input_users_bank[self.usernames[0]] - bet_value
        )
        assert next(self.game.players.passed) == self.users_list[1].player_at(self.game)
