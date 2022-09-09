from games.models import Game
import pytest

@pytest.fixture
def game(request, bunch_of_users):
    return Game(players=bunch_of_users, commit=True)

