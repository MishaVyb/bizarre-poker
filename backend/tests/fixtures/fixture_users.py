import pytest
from core.utils import get_func_name
from users.models import User


@pytest.fixture
def vybornyy():
    username = get_func_name()
    return User.objects.create_user(username=username, password=username)


@pytest.fixture
def simusik():
    username = get_func_name()
    return User.objects.create_user(username=username, password=username)


@pytest.fixture
def barticheg():
    username = get_func_name()
    return User.objects.create_user(username=username, password=username)


@pytest.fixture
def someuser():
    username = get_func_name()
    return User.objects.create_user(username=username, password=username)


@pytest.fixture(
    params=[
        pytest.param(1, id='one user'),
        pytest.param(2, id='two users'),
        pytest.param(3, id='three users'),
        pytest.param(7, id='seven users'),
    ]
)
def bunch_of_users(request):
    return [
        User.objects.create_user(username=f'test_user_{i}', password=f'test_user_{i}')
        for i in range(request.param)
    ]
