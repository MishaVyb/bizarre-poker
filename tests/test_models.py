import logging
from typing import Any

import pytest
from core.functools.utils import init_logger
from django.db import IntegrityError, models
from games.backends.cards import CardList
from games.models import Game, Player
from games.models.player import PlayerBet, PlayerManager, PlayerQuerySet
from games.services import configurations
from users.models import User

from tests.base import BaseGameProperties

logger = init_logger(__name__, logging.INFO)


@pytest.mark.django_db
class TestGameModel:
    @pytest.mark.parametrize(
        'init_kwargs, expected',
        [
            pytest.param(
                dict(
                    deck=CardList('Ace-H', 'red'),
                    table=CardList('10-2'),
                ),
                (CardList('Ace-H', 'red'), CardList('10-2')),
                id='Simple test',
            ),
            pytest.param(
                dict(
                    deck=None,
                    table=None,
                ),
                ([], []),
                id='None value will failed. Bacause it`s forbidden for CardList Field.',
                marks=pytest.mark.xfail,
            ),
        ],
    )
    def test_game_creation(self, init_kwargs, bunch_of_users, expected):
        # act
        Game(**init_kwargs, players=bunch_of_users, commit=True)

        # assertion
        game: Game = Game.objects.first()
        assert isinstance(game.deck, CardList)
        assert isinstance(game.table, CardList)
        assert expected == (game.deck, game.table)
        assert all(map(lambda u, p: u == p.user, bunch_of_users, game.players))

    @staticmethod
    @pytest.mark.parametrize(
        'data, exception, match',
        [
            pytest.param(
                'Ace-H',
                TypeError,
                "CardListField stores only CardList instances, not <class 'str'>",
            ),
            pytest.param(
                '',
                TypeError,
                "CardListField stores only CardList instances, not <class 'str'>",
            ),
            pytest.param(
                [],
                TypeError,
                "CardListField stores only CardList instances, not <class 'list'>",
            ),
        ],
    )
    def test_game_creation_raises(data: Any, exception: type, match: str):
        with pytest.raises(exception, match=match):
            Game.objects.create(deck=data, table=data)

    def test_blank_field(self):
        # with empty cardlist argument
        empty_list = CardList()
        game: Game = Game.objects.create(deck=empty_list, table=empty_list)
        assert isinstance(game.deck, CardList)
        assert game.deck is empty_list
        assert game.table is empty_list

        # no arguments for create
        game = Game.objects.create()
        assert isinstance(game.deck, CardList)
        assert (
            game.deck is not empty_list
        ), 'is not, because new empty list creates inside'
        assert game.deck == empty_list, 'but equal'
        assert (
            game.table is not empty_list
        ), 'is not, because new empty list creates inside'
        assert game.table == empty_list, 'but equal'

        # load form db
        game = Game.objects.get(pk=2)
        assert isinstance(game.deck, CardList)

    @pytest.mark.skip(
        'Game model not inheretted from ChangedFieldsMixin anymore. '
        'So this test has no sence. '
    )
    def test_get_changed_fields(self):
        # create game
        game: Game = Game.objects.create()
        changed = game.get_changed_fields()
        assert changed == {}

        game.table = CardList('Ace|H', 'Ace|D')
        changed = game.get_changed_fields()
        assert changed == {'table': CardList('Ace|H', 'Ace|D')}
        game.save()

        # new query to db
        game = Game.objects.get(pk=1)
        game.table = CardList('red')
        changed = game.get_changed_fields()
        assert changed == {'table': CardList('red')}

        game.save()
        changed = game.get_changed_fields()
        assert changed == {}

    @pytest.mark.skip('Test is not implemented yet')
    def test_clean_rises(self, game):
        raise NotImplementedError

    @pytest.mark.django_db(transaction=True)
    def test_unique_constraints(self, vybornyy: User, simusik: User):
        game: Game = Game(players=[vybornyy, simusik], commit=True)

        # assert related names
        assert vybornyy.players.first().game == game

        # unique raises
        with pytest.raises(IntegrityError, match='UNIQUE constraint failed'):
            game.players.create(user=vybornyy, position=1, is_host=False)
        with pytest.raises(IntegrityError, match='UNIQUE constraint failed'):
            Game(players=[vybornyy, vybornyy, simusik], commit=True)

        # no raises for another game
        Game(players=[vybornyy, simusik], commit=True)

    def test_deck_generator_default(self):
        field_default = Game._meta.get_field('deck_generator').default
        assert callable(field_default)
        assert field_default() == configurations.DEFAULT.deck_container_name


@pytest.mark.django_db
class TestPlayerModel:
    def test_clean_rises(self, game: Game):
        if not game.players:
            pytest.skip('test has no sense for game without players')

        with pytest.raises(IntegrityError):
            game.players.host.update(is_host=False)
        with pytest.raises(IntegrityError):
            game.players[0].update(position=123)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestPlayerManager(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg')

    def test_player_manager(self):
        assert isinstance(Player.objects, models.Manager)
        assert hasattr(Game, 'players'), 'players is a RelatedDescriprot class'
        assert not isinstance(Game.players, PlayerManager), (
            'There are no access to releted manager `players` through class, '
            'it`s allowed only for instances'
        )

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
        assert self.game.players.all()[0].user.username == 'vybornyy'
        assert self.game.players.all()[0].position == 0
        assert self.game.players.after_dealer[0].user.username == 'simusik'
        assert self.game.players.after_dealer[0].position == 1

    def test_players_attributes(self):
        # dealer
        assert self.game.players[0].is_dealer
        assert not self.game.players[1].is_dealer
        assert [p.is_dealer for p in self.game.players] == [True, False, False]

        # other_players
        expected = [self.players['simusik'], self.players['barticheg']]
        assert list(self.game.players.dealer.other_players) == expected

    def test_players_after_dealer(self):
        expected = (self.users_list[1], self.users_list[2], self.users_list[0])
        assert list(self.game.players.after_dealer) == [
            u.player_at(self.game) for u in expected
        ]

    def test_player_bet(self):
        self.players['simusik'].bets.create(value=15)
        self.players['simusik'].bets.create(value=25)
        self.players['barticheg'].bets.create(value=10)

        # bet total
        assert self.game.players[1].bet_total == 40  # via annotated field at player
        assert self.game.players[1].bets.total == 40  # via qs property
        assert self.game.players.get(bet_total=40) == self.players['simusik']

        # 0 if player was not make a bet
        assert self.game.players[0].bet_total == 0
        assert self.game.players[0].bets.total == 0

        # bot None via special annotation method
        qs = PlayerManager._annotate_bet_total_with_none(self.game.players)
        assert qs[0].bet_total_none is None

        # узнаем кто не сделал ставку
        expected = [self.game.players[0]]
        assert list(self.game.players.without_bet) == expected

        # узнаем наиболшую ставку в игре
        assert self.game.players.with_max_bet.bet_total == 40
        assert self.game.players.aggregate_max_bet() == 40

        # bets equality
        assert self.game.players.check_bet_equality() is False
        self.players['barticheg'].bets.create(value=30)
        self.players['vybornyy'].bets.create(value=40)
        assert self.game.players.check_bet_equality() is True

        # if there are no bets at alll
        PlayerBet.objects.all().delete()
        assert self.game.players.check_bet_equality() is True

        # if there are only one bet
        self.players['simusik'].bets.create(value=15)
        assert self.game.players.check_bet_equality() is False

        # order by bet
        q = self.game.players.order_by_bet
        assert q[0] == self.players['barticheg']
        assert q[1] == self.players['vybornyy']
