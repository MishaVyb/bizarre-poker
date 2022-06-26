from typing import Any, Pattern
from django.db import IntegrityError
import pytest
from games.backends.cards import Card, CardList

from games.models import Game, Player


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

