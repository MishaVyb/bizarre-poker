"""

warnings:
user_admin is default

developing:
[ ] -> QuerySet[AbstractBaseUser] type error

"""
import pytest
from django.contrib.auth import get_user_model
from games.services.cards import CardList
from games.models import Game
from users.models import User


@pytest.fixture
def admin_user():
    return User.objects.create(username='admin_user', password='12345678')

@pytest.fixture
def vybornyy():
    return User.objects.create(username='vybornyy', password='12345678')

@pytest.fixture
def barticheg():
    return User.objects.create(username='barticheg', password='12345678')

@pytest.fixture
def simusik():
    return User.objects.create(username='simusik', password='12345678')

@pytest.fixture
def arthur_morgan():
    return User.objects.create(username='arthur_morgan', password='12345678')



@pytest.fixture(
    params=[
        pytest.param(0, id='no users'),
        pytest.param(1, id='one user'),
        pytest.param(2, id='two users'),
        pytest.param(3, id='two users'),
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


