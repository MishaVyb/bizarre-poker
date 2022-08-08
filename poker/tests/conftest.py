"""
developing:
[ ] create one main conftest file

"""
import pytest
from users.models import User


@pytest.fixture
def admin_user():
    return User.objects.create(username='admin_user')

@pytest.fixture
def vybornyy():
    return User.objects.create(username='vybornyy')
