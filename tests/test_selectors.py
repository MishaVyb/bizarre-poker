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
        game.players[1].bets.append(15)
        assert game.players[1].bet_total == 15

        game.players[1].save()
        assert self.players['simusik'].bets == [15]

        # [2] place more bets
        game.players[1].bets.append(25)
        game.players[2].bets.append(10)

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
        game.players[2].bets.append(30)
        with temporally(game.players[0], is_active=False):  # player say `pass`
            assert game.players.check_bet_equality() is True

        # [6] clear bets
        for player in game.players:
            player.bets.clear()

        # [7] bets equality
        assert game.players.check_bet_equality() is True

        # if there are only one bet with 0 value
        game.players[1].bets.append(0)
        assert game.players.check_bet_equality() is True  # still true

        # [8] next_betmaker
        expected = [
            game.players[2],  # no bets
            game.players[0],  # no bets
            game.players[1],  # bet = 0
        ]
        assert game.players.next_betmaker == expected[0]

        game.players[0].bets.append(10)
        game.players[1].bets.append(20)
        expected = [
            game.players[2],  # no bets
            game.players[0],  # bet = 10
            game.players[1],  # bet = 0 + 20
        ]
        assert game.players.next_betmaker == expected[0]

        game.players[2].bets.append(20)
        game.players[0].bets.append(20)
        expected = [
            game.players[1],  # bet = 0 + 20
            game.players[2],  # bet = 20
            game.players[0],  # bet = 10 + 20
        ]
        assert game.players.next_betmaker == expected[0]


