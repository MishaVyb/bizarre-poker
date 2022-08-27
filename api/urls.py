from api.views import GamesViewSet, PlayersViewSet, BetViewSet
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'api'

router = DefaultRouter()
router.register('games', GamesViewSet)
router.register(
    r'games/(?P<game_pk>\d+)/players', PlayersViewSet, basename='players'
)
router.register(
    r'games/(?P<game_pk>\d+)/bet', BetViewSet, basename='bids'
)

urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/', include('djoser.urls.jwt')),
    path('v1/', include('djoser.urls')),
    path('v1/api-token-auth/', obtain_auth_token),
]