from django.contrib import admin, auth
from django.urls import include, path

from games.views import IndexView

app_name = 'games'

urlpatterns = [
    path('', IndexView.as_view(), name='index')
]