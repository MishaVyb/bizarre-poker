from typing import Any
from django.db import IntegrityError

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser

from core.functools.utils import isinstance_items
from games.backends.cards import CardList, Stacks
from games.backends.combos import CLASSIC_COMBOS
from games.models import Game, Player, GAME_ACTIONS, BaseGameAction, RequirementError
from users.models import User


@pytest.mark.django_db
class TestUserModel:
    def test_user_fiilds(self, admin_user):
        assert hasattr(admin_user, '_players')


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
                id="""None is okey, because it will not provide to super init method
                and replaced to empty card list.
                """,
            ),
            pytest.param(
                dict(
                    deck=None,
                    table=None,
                ),
                ([], []),
                id='.....',
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

    @pytest.mark.django_db(transaction=True)
    def test_unique_constraints(self, admin_user, vybornyy: User):
        """Правило: у одного юзера может быть много плееров, но у этих плееров
        должны быть разные геймы. То есть один юзер не может играть в одну игру
        несколькими плеерами"""

        game: Game = Game.objects.create()
        game.players_manager.create(user=admin_user, hand=CardList('Ace|S'))

        # assert related names
        assert admin_user.players.first().hand == CardList('Ace|S')
        assert admin_user.players.first().game == game

        # unique raises
        with pytest.raises(
            IntegrityError,
            match='UNIQUE constraint failed: games_player.user_id, games_player.game_id'
        ):
            game.players_manager.create(user=admin_user, hand=CardList('10-H'))

        with pytest.raises(
            ValueError,
            match='vybornyy already playing in...',
        ):
            Game(players=[admin_user, vybornyy, vybornyy], commit=True)

        # no raises for another game
        another_game: Game = Game.objects.create()
        another_game.players_manager.create(user=admin_user, hand=CardList('9-H'))

    def test_game_all_actions_force_requirements(self, game_with_bunch_of_players):
        game_cicle_amount = 7
        game: Game = game_with_bunch_of_players


        assert game.current_action == GAME_ACTIONS['setup']

        for i in range(len(GAME_ACTIONS)):
            game.current_action.game = game
            try:
                game.current_action.pre_call()
            except RequirementError as e:
                pass
            finally:
                game.current_action()
                game.current_action.post_call()

        assert game.current_action == GAME_ACTIONS['setup']

    @pytest.mark.parametrize(
        'table, hands, action, expected',
        [
            pytest.param(
                CardList('Ace|H', 'Ace|D', 'King|C', '5-c', '7-s'),   # table
                (
                    CardList('10-s', '9-s'),    # vybornyy hand
                    CardList('Ace|H', '2-h'),   # bart_barticheg hand
                ),
                GAME_ACTIONS['opposing'],
                (
                    # expected combo vybornyy
                    ('one pair', {
                        'rank': [CardList('Ace|H', 'Ace|D')]
                    }),
                    # expected combo bart_barticheg
                    ('three of kind', {
                        'rank': [CardList('Ace|H', 'Ace|H', 'Ace|D')]
                    })
                ),
                id='simple test'
            ),
            pytest.param(
                CardList('Ace|H', 'Jack|D', 'King|C', '5-c', '7-s'),   # table
                (
                    CardList('10-s', '9-s'),    # vybornyy hand
                    CardList('Ace|H', '2-h'),   # bart_barticheg hand
                ),
                GAME_ACTIONS['opposing'],
                (
                    # expected combo vybornyy
                    ('high card', {
                        'highest_card': [CardList('Ace|H')]
                    }),
                    # expected combo bart_barticheg
                    ('one pair', {
                        'rank': [CardList('Ace|H', 'Ace|H')]
                    })
                ),
                id='high card combo'
            ),
        ],
    )
    def test_players_combo_after_game_method(
        self,
        table: CardList,
        hands: Stacks,
        action: BaseGameAction,
        expected,
        game_vybornyy_vs_bart: Game,
        vybornyy: User,
        bart_barticheg: User,
    ):
        # get custom deck from input data:
        test_deck = CardList()
        test_deck.extend(table)
        for cards in zip(*reversed(hands), strict=True):
            test_deck.extend(cards)

        # set our test deck to the game
        game = game_vybornyy_vs_bart
        game.deck_generator_shuffling = False
        game.deck_generator = test_deck.copy()

        act = False
        while not act:
            if game.current_action == action:
                act = True

            game.current_action.game = game
            try:
                game.current_action.pre_call()
            except RequirementError as e:
                pass
            finally:
                game.current_action()
                game.current_action.post_call()

        # assertion:
        for player, hand, (name, stacks) in zip(
            game.players, hands, expected, strict=True
        ):
            assert player.hand == list(reversed(hand))
            assert player.combo.name == name
            for key in CLASSIC_COMBOS.get(player.combo.name).cases.keys():
                assert player.combo[key] == stacks[key]

        #game.teardown()

    def test_deck_generator_default(self):
        assert Game._meta.get_field('deck_generator').default == (
            'Decks.standart_52_card_deck_plus_jokers'
        )


@pytest.mark.django_db
class TestPlayerComboModel:


    @pytest.mark.parametrize(
        'hand, expected_name, expected_cases',
        [
            pytest.param(
                CardList('Ace|H', 'Ace|D'),
                'one pair',
                {
                    'rank': [CardList('Ace|H', 'Ace|D')],
                },
            ),
            pytest.param(
                CardList('Ace|H', 'King|D'),
                'high card',
                {
                    'highest card': [CardList('Ace|H')],
                },
            ),
        ],
    )
    def test_setup(
        self,
        admin_user: User,
        game_with_bunch_of_players: Game,
        hand: CardList,
        expected_name: str,
        expected_cases: dict[str, Stacks],
    ):
        # act:
        game = game_with_bunch_of_players

        # add main test player to the game
        player: Player = admin_user.players_manager.create(game=game, hand=hand)
        player.combo.setup()

        # get player by another query to db:
        player = Player.objects.get(user=admin_user)
        
        # assertion:
        assert isinstance(player.combo.name, str)
        assert isinstance_items(player.combo.rank, list, CardList)
        assert isinstance_items(player.combo.suit, list, CardList)
        assert isinstance_items(player.combo.row, list, CardList)
        assert isinstance_items(player.combo.highest_card, list, CardList)

        assert player.combo.name == expected_name
        assert player.combo.priority == CLASSIC_COMBOS.get(expected_name).priority
        assert player.combo.rank == expected_cases.get('rank', [])
        assert player.combo.suit == expected_cases.get('suit', [])
        assert player.combo.row == expected_cases.get('row', [])
        assert player.combo.highest_card == expected_cases.get('highest card', [])

    def test_double_setup(self):
        pass


class TestStacksField:
    pass
