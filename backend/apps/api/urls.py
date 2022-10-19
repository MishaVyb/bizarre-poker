from api.views import GamesViewSet, PlayersPreformViewSet, PlayersViewSet, ActionsViewSet
from django.urls import include, path, re_path, reverse_lazy
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic.base import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

app_name = 'api'

########################################################################################
# doc
########################################################################################

schema_view = get_schema_view(
    openapi.Info(
        title="Bizarre Poker API",
        default_version='v1',
        description="Internal REST API to link fronted and backend parts of app.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="vbrn.mv@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    re_path(
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    re_path(
        r'^swagger/$',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui',
    ),
    re_path(
        r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'
    ),
]

########################################################################################
# auth
########################################################################################

urlpatterns += [
    path('v1/auth/', include('djoser.urls')),
    path('v1/auth/', include('djoser.urls.authtoken')),
]

########################################################################################
# games
########################################################################################

router = DefaultRouter()
router.register('games', GamesViewSet)
router.register(r'games/(?P<pk>\d+)/actions', ActionsViewSet, basename='actions')
router.register(r'games/(?P<pk>\d+)/players', PlayersViewSet, basename='players')
router.register(r'games/(?P<pk>\d+)/playersPreform', PlayersPreformViewSet, basename='players_preform')

urlpatterns += [
    path('v1/', include(router.urls)),
]

########################################################################################
# main api root
########################################################################################

urlpatterns += [
    path('', RedirectView.as_view(url=reverse_lazy('api:schema-swagger-ui'))),
]
