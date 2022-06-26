from django.contrib import admin, auth
from django.urls import include, path, reverse, reverse_lazy
from django.views.generic.list import ListView
from django.views.generic.base import RedirectView
from games import models

from games.views import GameView, IndexView, UserGamesListView

app_name = 'games'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('games/<int:pk>/', GameView.as_view(), name='game'),
    path('games/', RedirectView.as_view(url=reverse_lazy('games:index')), name='games'),
    path('games/all/', ListView.as_view(
            model = models.Game,
            context_object_name = 'games'
        ),
        name='all'),
    path('games/user/', UserGamesListView.as_view(), name='user'),
]