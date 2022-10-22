import pytest
from games.models.game import Game
from users.models import User


@pytest.fixture
def game(request, bunch_of_users):
    return Game(players=bunch_of_users, commit=True)

@pytest.fixture
def simple_game(vybornyy: User, simusik: User, barticheg: User):
    return Game(players=[vybornyy, simusik, barticheg], commit=True)
