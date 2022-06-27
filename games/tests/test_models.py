from typing import Any, Pattern
from django.db import IntegrityError
import pytest
from games.backends.cards import Card, CardList, Stacks
from games.backends.combos import CLASSIC_COMBOS, ComboStacks

from games.models import Game, Player, PlayerCombo

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser


@pytest.mark.django_db
class TestUserModel:
    def test_user_fiilds(self, admin_user):
        assert hasattr(admin_user, 'players')


@pytest.mark.django_db
class TestGameModel:

    def test_game_creation(self):
        deck = CardList('Ace-H', 'red')
        table = CardList('10-2')
        game: Game = Game.objects.create(deck=deck, table=table)
        assert deck, table == (game.deck, game.table)


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
                None,
                TypeError,
                "CardListField stores only CardList instances, not <class 'NoneType'>",
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
        assert game == Game(pk=1, deck=empty_list, table=empty_list)

        # no arguments for create
        game = Game.objects.create()
        assert isinstance(game.deck, CardList)
        assert game == Game(pk=2, deck=empty_list, table=empty_list)

        # load form db
        game = Game.objects.get(pk=2)
        assert isinstance(game.deck, CardList)


    @pytest.mark.django_db(transaction=True)
    def test_unique_constraints(self, admin_user):
        """Правило: у одного юзера может быть много плееров, но у этих плееров
        должны быть разные геймы. То есть один юзер не может играть в одну игру
        несколькими плеерами"""

        game: Game = Game.objects.create()
        game.players.create(user=admin_user, hand=CardList('Ace|S'))

        # assert related names
        assert admin_user.players.first().hand == CardList('Ace|S')
        assert admin_user.players.first().game == game

        # assert unique
        with pytest.raises(
            IntegrityError,
            match='UNIQUE constraint failed: games_player.user_id, games_player.game_id',
        ):
            game.players.create(user=admin_user, hand=CardList('10-H'))

        another_game: Game = Game.objects.create()
        another_game.players.create(user=admin_user, hand=CardList('9-H'))


@pytest.mark.django_db
class TestGameProcessModel():
    pass


@pytest.mark.django_db
class TestPlayerComboModel():


    def test_setup(self, admin_user: AbstractBaseUser):
        expected_name = 'one pair'
        expected_cases: dict[str, Stacks] = {'rank': [CardList('Ace|H', 'Ace|D')]}

        game: Game = Game.objects.create()
        hand = CardList('Ace|H', 'Ace|D')
        player: Player = Player.objects.create(user=admin_user, game=game, hand=hand)
        combo: PlayerCombo = PlayerCombo.objects.create(player=player)
        stacks = ComboStacks()

        kind = stacks.track_and_merge(player.hand)

        assert kind == CLASSIC_COMBOS.get(expected_name)

        combo.setup(combo_kind=kind, combo_stacks=stacks)
        assert Player.objects.get(game=game).combo.name == expected_name
        assert Player.objects.get(game=game).combo.rank == expected_cases['rank']
        assert Player.objects.get(game=game).combo.suit == []
        assert Player.objects.get(game=game).combo.row == []
        assert Player.objects.get(game=game).combo.highest_card == []

        






