




from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
import pytest
from users.models import User
from django.contrib.auth.models import AnonymousUser

@pytest.mark.django_db
@pytest.mark.parametrize('auth', [
    pytest.param(
        True,
        id='clint is logged in by admin_user'
    ),
    pytest.param(
        False,
        id='clint is logged in by admin_user'
    ),
])
def test_user_proxy_middleware_type_checking(auth, admin_user: User, client: Client):
    assert isinstance(admin_user, User)
    if auth:
        client.force_login(admin_user)

    responce: HttpResponse = client.get(reverse('games:index'))
    assert isinstance(responce, HttpResponse)
    user = responce.context.get('user')
    assert user is not None
    assert isinstance(user, User if auth else AnonymousUser)
    # another assertion inside view method

