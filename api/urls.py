from api.views import GamesViewSet
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

app_name = 'api'

router = DefaultRouter()
router.register('games', GamesViewSet)
# router.register(
#     r'posts/(?P<post_id>\d+)/comments', CommentViewSet, basename='comments'
# )
# router.register('groups', GroupViewSet)
# router.register('follow', FollowViewSet, basename='follow')

urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/', include('djoser.urls.jwt')),
    path('v1/', include('djoser.urls')),
    path('v1/api-token-auth/', obtain_auth_token),
]