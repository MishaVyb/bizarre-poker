import pytest
from users.models import User
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.test import APIClient

from tests.base import APIGameProperties, BaseGameProperties



@pytest.mark.django_db
class TestApiMidlware(APIGameProperties):
    usernames = ('user',)

    def test_user_proxy_middleware_by_apy(self, setup_clients):
        assert isinstance(self.users['user'], User)

        response = self.clients['user'].get('/api/v1/games/')
        assert isinstance(response, Response)

        user = response.data.serializer.context['request'].user
        assert isinstance(user, User), 'User should be UserProxy instance'

        self.response_data = self.clients['user'].get('/api/v1/test/').data
        self.make_log()

