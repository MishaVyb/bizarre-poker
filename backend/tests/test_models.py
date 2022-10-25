import logging
from operator import attrgetter
from timeit import timeit
from typing import Any

import pytest
from core.utils import (ProcessingTimer, change_loggers_level, init_logger,
                        processing_timer)
from django.db import IntegrityError
from django.db.models import Prefetch
from games.models import Game, Player
from games.models.managers import PlayerManager, PlayerQuerySet
from games.services import actions
from games.services.cards import CardList
from games.services.processors import AutoProcessor, BaseProcessor
from users.models import Profile, User

from tests.base import BaseGameProperties
from tests.tools import ExtendedQueriesContext

logger = init_logger(__name__)


@pytest.mark.django_db
class TestGameModel:
    def test_game_creation(self, bunch_of_users):
        # arrange
        deck = CardList('Ace-H', 'red')
        table = CardList('10-2')

        # act
        game = Game(deck=deck, table=table, players=bunch_of_users, commit=True)

        # assert player selector after Game creation
        # it's avaliable and Player contains the same User instance!
        assert all([p.user is u for p, u in zip(game.players, bunch_of_users)])

        # new query without prefetch_related
        game = Game.objects.first()

        # assert deck and table
        assert isinstance(game.deck, CardList)
        assert isinstance(game.table, CardList)
        assert game.deck, game.table == (deck, table)

        # no player selector - no rises, but warning log
        game.players

        game.select_players()
        assert game.players
        assert all(map(lambda u, p: u == p.user, bunch_of_users, game.players))

        # assert init clean
        assert all(map(attrgetter('is_active'), game.players))
        assert game.players[0].is_host is True
        assert not any(map(attrgetter('is_host'), game.players[1:]))

        # assert init clean - positions
        result = list(map(attrgetter('position'), game.players))
        expected = list(range(len(bunch_of_users)))
        assert result == expected

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
            pytest.param(
                None,
                TypeError,
                "CardListField stores only CardList instances, not <class 'NoneType'>",
            ),
        ],
    )
    def test_cardlist_field_raises(data: Any, exception: type, match: str):
        with pytest.raises(exception, match=match):
            Game.objects.create(deck=data, table=data)
        with pytest.raises(exception, match=match):
            Game(deck=data, table=data).save()

    def test_cardlist_field_blank(self):
        # with empty cardlist argument
        empty_list = CardList()
        game: Game = Game.objects.create(deck=empty_list)
        assert isinstance(game.deck, CardList)
        assert game.deck is empty_list  # the same

        # no arguments for create
        game = Game.objects.create()
        assert isinstance(game.deck, CardList)
        assert game.deck is not empty_list  # is not - new empty list creates inside
        assert game.deck == empty_list

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

    @pytest.mark.django_db(transaction=True)
    def test_unique_constraints(self, vybornyy: User, simusik: User):
        game: Game = Game(players=[vybornyy, simusik], commit=True)

        # unique raises
        with pytest.raises(IntegrityError, match='UNIQUE constraint failed'):
            game.players_manager.create(user=vybornyy, position=1, is_host=False)
        with pytest.raises(IntegrityError, match='UNIQUE constraint failed'):
            Game(players=[vybornyy, vybornyy, simusik], commit=True)

        # no raises for another game
        Game(players=[vybornyy, simusik], commit=True)



@pytest.mark.django_db
class TestGamePlayersInterface(BaseGameProperties):
    @property
    def game_no_player_selector(self):
        return Game.objects.get(pk=self.game_pk)

    def test_game_prefecth_related(self, setup_game):
        # [01] Test no prefetch. Get game object with empty prefetch_lookups
        game = self.game_no_player_selector

        assert isinstance(game.players_manager, PlayerManager)
        assert isinstance(game.players_manager.all(), PlayerQuerySet)
        with ExtendedQueriesContext() as context:
            [p for p in game.players_manager]  # ask to all players
            [p for p in game.players_manager]  # ask to all players
            [p for p in game.players_manager]  # ask to all players
            assert context.amount == 3

        # [02] test Prefetch to attribute
        # RESULT: it makes list of players
        lookup = Prefetch(lookup='players_manager', to_attr='prefetched_players')
        game = Game.objects.prefetch_related(lookup).get(pk=self.game_pk)
        assert hasattr(game, 'prefetched_players')
        assert isinstance(game.prefetched_players, list)  # !!!!

        with ExtendedQueriesContext() as context:
            [p for p in game.prefetched_players]  # ask to players -- no db evulation
            assert not context.captured_queries

        # [03] test prefetch players for players_manager
        # RESULT: it cashe `players_manager.all()` but not other filters
        lookup = 'players_manager'
        game = Game.objects.prefetch_related(lookup).get(pk=self.game_pk)
        new_user = User.objects.create(username='new_user', password='new_user')
        another_new_user = User.objects.create(
            username='another_new_user', password='another_new_user'
        )

        # no queries here:
        # instead of having to go to the database for the items, it will find them in a
        # prefetched QuerySet cache that was populated in a single query.
        assert isinstance(game.players_manager, PlayerManager)
        assert isinstance(game.players_manager.all(), PlayerQuerySet)
        with ExtendedQueriesContext() as context:
            [p for p in game.players_manager]  # ask to all players -- no db evulation
            [p for p in game.players_manager.all()]  # the same
            assert not context.captured_queries

            # ask to all active players makes new query because of filter
            [p for p in game.players_manager.active]
            assert context.amount == 1

            # and it`s not cached... ask again
            [p for p in game.players_manager.active]
            assert context.amount == 2

            # back to the qashed query again, cahe is stil here
            [p for p in game.players_manager]  # ask to all players -- no db evulation
            assert context.amount == 2

            # but what if we add new player? will it change a cash
            # RESULT: cache has not updated
            new_player = Player.objects.create(game=game, user=new_user)
            assert new_player not in [p for p in game.players_manager]  # not in cache
            assert new_player in game.players_manager.active  # but in new qs

            # okey, add new_player in another way, via game.players manager
            # RESULT: the same, cache has not updated
            another_new_player = game.players_manager.create(user=another_new_user)
            assert another_new_player not in [p for p in game.players_manager]
            assert another_new_player in game.players_manager.active

            # clear prefetch_related
            # RESULT: the same, cache has not updated
            game.players_manager.prefetch_related(None)
            assert another_new_player not in [p for p in game.players_manager]

    def test_select_players(self, setup_game):
        game = self.game_no_player_selector
        game.select_players()
        # [1]
        with ExtendedQueriesContext() as context:
            [p for p in game.players]  # db evulation
            [p for p in game.players]  # cache
            [p for p in game.players]  # cache

            # we use the same qury set at PlayerSelector - so it evulate db only once
            assert context.amount == 1

            game.players[0]  # also cache
            game.players[1]  # also cache
            game.players[2]  # also cache

        # [2]
        game = self.game_no_player_selector
        game.select_players()
        with ExtendedQueriesContext() as context:
            game.players[0]  # new query: LIMIT 1 OFFSET 0
            game.players[1]  # new query: LIMIT 1 OFFSET 1
            game.players[2]  # new query: LIMIT 1 OFFSET 2

            game.players[0]  # again db evulation -- no cashe
            game.players[1]
            game.players[2]
            assert context.amount == 6

        with ExtendedQueriesContext() as context:
            # force make db query and cashe result
            # result: cashe will be used
            game.select_players(force_cashing=True)
            assert context.amount == 1

            game.players[0]  # cashe
            [p for p in game.players]  # cache
            assert context.amount == 1

    def test_reselect_players(self, setup_game):
        game = self.game

        # add new player -- need to update prefetch_related
        assert len(game.players) == 3
        Player.objects.create(
            game=game, user=User.objects.create(username='user', password='user')
        )
        assert len(game.players) == 3  # still 3
        assert len(game.players_manager) == 3  # still 3

        with ExtendedQueriesContext() as context:
            game.reselect_players()
            assert game.players
            assert game.players[0]
            assert game.players[0].user
            assert game.players[0].user.username
            assert game.players[0].user.profile.bank
            assert context.amount == 1

    @pytest.mark.slow
    def test_selector_vs_manager_speed(self):
        # [1] old way - how it was before player selector
        self.game_pk = Game(players=self.users_list, commit=True).pk
        game = self.game_no_player_selector
        with processing_timer(logger) as timer_1:
            with ExtendedQueriesContext() as context_1:
                game.players_manager.host
                game.players_manager.active
                game.players_manager.after_dealer
                game.players_manager.after_dealer_all

        # [2] new way -- recomended
        self.game_pk = Game(players=self.users_list, commit=True).pk
        game = self.game # players prefethed and selected already inside |self.game|
        with processing_timer(logger) as timer_2:
            with ExtendedQueriesContext() as context_2:
                game.players.host
                game.players.active
                game.players.after_dealer
                game.players.after_dealer_all

        assert context_1.amount > context_2.amount
        assert timer_1 > timer_2

        # [3]
        # RESULT:
        # it's faster to use python methods to handle the same data
        # then making another specific query  (for small amount of data in my case)
        change_loggers_level(logging.ERROR)
        t1 = timeit(lambda: game.players_manager.after_dealer_all)  # order_by inside
        t2 = timeit(lambda: game.players.after_dealer_all)  # sort inside
        logger.info(f'\n{t1=}\n{t2=}')
        assert t1 > t2

    def test_queries_amount_select_players(self, setup_game):
        with ExtendedQueriesContext() as context:
            self.game
            # 1- SELECT game
            # 2- SELECT players (prefetche_related)
            # 3- SELECT users (prefetche_related)
            # 4- SELECT profile (prefetche_related)
            assert context.amount == 4, context.formated_quries

    def test_queries_amount_full_round(self, setup_game):
        game = self.game
        rounds = 1
        with ProcessingTimer(name=f'Timer for {rounds} rounds processing. '):
            with ExtendedQueriesContext(sql_report=True) as context:
                AutoProcessor(
                    game,
                    stop_after_rounds_amount=rounds,
                    autosave=False,
                ).run()
        assert context.amount == 0

    def test_queries_amount_game_objects_saving(self, setup_game):
        game = self.game
        user = self.users_list[0]

        with ExtendedQueriesContext() as context:
            actions.StartAction.run(game, user, autosave=False)
            assert context.amount == 0, context.formated_quries  # none SELECT queries

            # act save:
            BaseProcessor(game)._save_game_objects(BaseProcessor.STOP)

            # 1- UPDATE game
            # 4- for every player:
            #   1- UPDATE player
            #   2-3-4 check constaints...
            players = len(self.usernames)
            assert context.amount == 1 + 4 * players, context.formated_quries

    def test_select_players_change_values(self, setup_game):
        game = self.game

        # change player attribute -- okey
        assert game.players[0].is_active is True
        game.players[0].is_active = False
        assert game.players[0].is_active is False


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestPlayerManager(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg')

    @property
    def game_no_player_selector(self):
        return Game.objects.get(pk=self.game_pk)

    def test_player_manager(self):
        assert isinstance(Player.objects, PlayerManager)
        with pytest.raises(AttributeError):
            Player.objects.host         # method is forbidden for accessing via class

        # |players_manager| is a RelatedDescriprot class
        # there are no access to releted manager |players_manager| via class
        assert not isinstance(Game.players_manager, PlayerManager)

        # but obviosly coild be accessed via game instance
        self.game.players_manager.host


    def test_players_after_dealer(self):
        expected = [
            self.players_list[1],
            self.players_list[2],
            self.players_list[0],
        ]
        assert list(self.game.players_manager.after_dealer) == expected

    def test_player_queryset_cache(self):
        qs = Player.objects.filter(game=self.game)

        # --- NO CACHE ---
        vybornyy_object_1 = qs[0]
        vybornyy_object_2 = qs[0]

        # this objects equal
        assert vybornyy_object_1 == vybornyy_object_2
        # but not the same !!!
        assert vybornyy_object_1 is not vybornyy_object_2

        # changing attribute for one won`t changit for another
        vybornyy_object_1.is_active = False
        assert vybornyy_object_2.is_active is True

        # --- CACHE Query Set ---
        # but if a call for full query before it will be cached
        [p for p in qs]
        vybornyy_object_1 = qs[0]
        vybornyy_object_2 = qs[0]

        # therefore they are the same objects
        assert vybornyy_object_1 is vybornyy_object_2

        # now it looks like list and has the same objects insede
        qs[0].is_active = False
        assert vybornyy_object_1.is_active is False
        assert vybornyy_object_2.is_active is False

        # but if I call for the same query again with no saving previous qs objects
        # it will create new qs and `evulated` it again

        another_qs = Player.objects.filter(game=self.game)
        assert qs is not another_qs
        assert qs[0] is not another_qs[0]
        assert another_qs[0].is_active is True



@pytest.mark.django_db
class TestUserProfileModels:

    def test_profile_creation(self):
        User.objects.create(username='vybornyy', password='vybornyy')
        assert Profile.objects.get(user__username='vybornyy')

        with pytest.raises(RuntimeError):
            User.objects.bulk_create([User(username='simusik', password='simusik')])
        
