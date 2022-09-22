import pytest
from core.functools.decorators import temporally
from core.functools.utils import init_logger

from tests.base import BaseGameProperties
from tests.tools import ExtendedQueriesContext

logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestPlayerSelector(BaseGameProperties):
    def test_players_ordering(self):
        game = self.game
        assert game.players[0].user.username == 'vybornyy'
        assert game.players[0].position == 0

    def test_after_dealer_all(self):
        game = self.game
        game.players[1].is_active = False

        expected = [
            self.players_list[1],
            self.players_list[2],  # passed player sitll represents here
            self.players_list[0],
        ]
        assert list(game.players.after_dealer_all) == expected

    def test_after_dealer(self):
        game = self.game
        game.players[2].is_active = False

        expected = [
            self.players_list[1],
            # self.players_list[2], # passed player is not represent here
            self.players_list[0],
        ]
        assert list(game.players.after_dealer) == expected

    def test_player_dealer(self):
        # Test that default annotation by PlayerManager is still there
        game = self.game
        assert [p.is_dealer for p in game.players] == [True, False, False]

    def test_player_other_players_property(self):
        expected = [self.players['simusik'], self.players['barticheg']]
        assert self.game.players.dealer.other_players == expected

    def test_player_bet(self):
        game = self.game

        assert game.players[1].bet_total == 0
        new_bet = game.players[1].bets.create(value=15)

        # [1] bet contains the same player instance
        assert game.players[1] is new_bet.player
        assert game.players[1].bet_total == 15
        assert (
            self.players['simusik'].bet_total == 15
        )  # check: real data at db the same

        # [2] place more bets
        game.players[1].bets.create(value=25)
        game.players[2].bets.create(value=10)

        assert game.players[0].bet_total == 0  # 0 if player was not make a bet
        assert game.players[1].bet_total == 40
        assert game.players[2].bet_total == 10

        # [3] without bet
        assert next(game.players.without_bet) is game.players[0]

        # [4] current max bet
        assert game.players.with_max_bet is game.players[1]
        assert game.players.aggregate_max_bet() == 40

        # [5] bets equality
        assert game.players.check_bet_equality() is False

        # make them equal or pass
        game.players[2].bets.create(value=30)
        with temporally(game.players[0], is_active=False):  # player say `pass`
            assert game.players.check_bet_equality() is True

        # [6]
        # 6.1 delete all bets at this game
        # 6.2 update annotation
        with ExtendedQueriesContext() as context:
            game.players_manager.all_bets().delete()
            game.players_manager.update_annotation(bet_total=0)
            assert context.amount == 1

        assert game.players[0].bet_total == 0
        assert game.players[1].bet_total == 0
        assert game.players[2].bet_total == 0

        # [7] bets equality
        assert self.game.players_manager.check_bet_equality() is True

        # if there are only one bet with 0 value
        game.players[1].bets.create(value=0)
        assert self.game.players_manager.check_bet_equality() is True  # still true

        # [8] order by bet
        expected = [
            game.players[2],  # no bets
            game.players[0],  # no bets
            game.players[1],  # bet = 0
        ]
        assert list(self.game.players.order_by_bet) == expected

        game.players[0].bets.create(value=10)
        game.players[1].bets.create(value=20)
        expected = [
            game.players[2],  # no bets
            game.players[0],  # bet = 10
            game.players[1],  # bet = 0 + 20
        ]
        assert list(self.game.players.order_by_bet) == expected

        game.players[2].bets.create(value=20)
        game.players[0].bets.create(value=20)
        expected = [
            game.players[1],  # bet = 0 + 20
            game.players[2],  # bet = 20
            game.players[0],  # bet = 10 + 20
        ]
        assert list(self.game.players.order_by_bet) == expected

    def test_player_bet_another_player_instance(self):
        # be carefull here
        # we operate with single game instance that contains certain players instances
        # call for another player instance won't make affect to game player
        game = self.game
        self.players_list[2].bets.create(value=100)
        assert game.players.aggregate_max_bet() == 0

        # but if prefetch_players again
        game = self.game
        assert game.players.aggregate_max_bet() == 100  # bet will be therer

    def test_aggregate_min_users_bank_no_quries(self):
        game = self.game
        with ExtendedQueriesContext() as context:
            assert game.players.aggregate_min_users_bank()
            assert context.amount == 0
