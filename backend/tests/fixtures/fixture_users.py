import pytest
from core.utils import get_func_name
from users.models import User


@pytest.fixture
def vybornyy():
    username = get_func_name()
    user: User = User.objects.create(username=username, password=username)
    user.set_password(user.username)    # othrwise password won't be supplyed
    user.save()
    return User.objects.get(username=user.username)

@pytest.fixture
def simusik():
    username = get_func_name()
    user: User = User.objects.create(username=username, password=username)
    user.set_password(user.username)
    user.save()
    return User.objects.get(username=user.username)

@pytest.fixture
def barticheg():
    username = get_func_name()
    user: User = User.objects.create(username=username, password=username)
    user.set_password(user.username)
    user.save()
    return User.objects.get(username=user.username)

@pytest.fixture
def someuser():
    username = get_func_name()
    user: User = User.objects.create(username=username, password=username)
    user.set_password(user.username)
    user.save()
    return User.objects.get(username=user.username)


@pytest.fixture(
    params=[
        pytest.param(1, id='one user'),
        pytest.param(2, id='two users'),
        pytest.param(3, id='three users'),
        pytest.param(7, id='seven users'),
    ]
)
def bunch_of_users(request):
    users = User.objects.bulk_create(
        [User(username=f'test user #{i}') for i in range(request.param)]
    )
    # 1- bulk_create returns list of users with no pk,
    # so there are another query to all objects
    # 2- objects.all() may contain other users (user_admin, vybornyy...)
    # so they are filtering by names
    return User.objects.filter(username__in=[user.username for user in users])
