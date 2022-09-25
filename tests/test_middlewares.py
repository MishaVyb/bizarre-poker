



from rest_framework.response import Response
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
import pytest
from users.models import User
from django.contrib.auth.models import AnonymousUser
from tests.base import BaseGameProperties, APIGameProperties

from rest_framework.test import APIClient

@pytest.mark.django_db
@pytest.mark.parametrize('auth', [
    pytest.param(
        True,
        id='clint is logged in by admin_user'
    ),
    pytest.param(
        False,
        id='clint is not logged in by admin_user'
    ),
])
def test_user_proxy_middleware(auth, admin_user: User, client: Client):
    assert isinstance(admin_user, User)
    if auth:
        client.force_login(admin_user)

    response: HttpResponse = client.get(reverse('games:index'))
    assert isinstance(response, HttpResponse)
    user = response.context.get('user')
    assert user is not None
    assert isinstance(user, User if auth else AnonymousUser)



@pytest.mark.django_db
class TestApiMidlware(APIGameProperties):
    usernames = ('user',)

    def test_user_proxy_middleware_by_apy(self, setup_clients):
        assert isinstance(self.users['user'], User)

        response = self.clients['user'].get('/api/v1/games/')
        assert isinstance(response, Response)

        user = response.data.serializer.context['request'].user
        assert isinstance(user, User)

        self.response_data = self.clients['user'].get('/api/v1/test/').data
        self.make_log()

