"""

warnings:
user_admin is default

developing:
[ ] -> QuerySet[AbstractBaseUser] type error

"""
import pytest
from django.contrib.auth import get_user_model
from games.backends.cards import CardList
from games.models import Game
from users.models import User


@pytest.fixture
def admin_user():
    u = User.objects.create(username='admin_user')
    return u


@pytest.fixture
def vybornyy():
    u = User.objects.create(username='vybornyy')
    return u


@pytest.fixture
def bart_barticheg():
    return User.objects.create(username='bart_barticheg')


@pytest.fixture(
    params=[
        pytest.param(0, id='no users'),
        pytest.param(1, id='one user'),
        pytest.param(2, id='two users'),
        pytest.param(7, id='seven users'),
    ]
)
def bunch_of_users(request):  # -> QuerySet[AbstractBaseUser]
    users = User.objects.bulk_create(
        [User(username=f'test user #{i}') for i in range(request.param)]
    )
    # 1- bulk_create returns list of users with no pk and id,
    # so there are another query to all objects
    # 2- objects.all() may contain other users (user_admin, vybornyy...)
    # so there are filtering by namse
    return User.objects.filter(
        username__in=[user.username for user in users]
    )


@pytest.fixture(
    params=[
        pytest.param(
            (
                CardList(),  # deck
                CardList(),  # table
            ),
            id='no table / no deck',
        )
    ]
)
def game_with_bunch_of_players(request, bunch_of_users):
    deck, table = request.param
    return Game(deck=deck, table=table, players=bunch_of_users, commit=True)


@pytest.fixture
def game_vybornyy_vs_bart(vybornyy, bart_barticheg):
    deck, table = (None, None)
    return Game(deck=deck, table=table, players=[vybornyy, bart_barticheg], commit=True)


@pytest.fixture
def urls():
    return {'game': 'games/<int:pk>/'}
