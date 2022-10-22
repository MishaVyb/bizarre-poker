import pytest
from rest_framework.response import Response
from users.models import User

from tests.base import APIGameProperties


@pytest.mark.django_db
class TestApiMidlware(APIGameProperties):
    usernames = ('user',)

    def test_user_proxy_middleware_by_apy(self, setup_clients):
        assert isinstance(self.users['user'], User)

        response = self.clients['user'].get('/api/v1/games/')
        assert isinstance(response, Response)

        user = response.data.serializer.context['request'].user
        assert isinstance(user, User), 'User should be UserProxy instance'

