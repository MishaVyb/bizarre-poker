from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from django.views.generic.list import ListView

from games import models
from games.views import GameView, IndexView, UserGamesListView

app_name = 'games'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('games/', RedirectView.as_view(url=reverse_lazy('games:index')), name='games'),
    path('games/<int:pk>/', GameView.as_view(), name='game'),
    path(
        'games/all/',
        ListView.as_view(model=models.Game, context_object_name='games'),
        name='all',
    ),
    path('games/user/', UserGamesListView.as_view(), name='user'),
]
