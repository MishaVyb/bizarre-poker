from api.views import GamesViewSet, PlayersViewSet, ActionsViewSet, TestView
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'api'

router = DefaultRouter()
router.register('games', GamesViewSet)
router.register(r'games/(?P<pk>\d+)/actions', ActionsViewSet, basename='actions')
router.register(
    r'games/(?P<game_pk>\d+)/players', PlayersViewSet, basename='players'
)



urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/test/', TestView.as_view()),

    path('v1/', include('djoser.urls.jwt')),
    path('v1/', include('djoser.urls')),
    path('v1/api-token-auth/', obtain_auth_token),
]