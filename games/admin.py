from django.contrib import admin

from games import models



@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('pk', 'stage_index', 'deck', 'table', 'players')
    list_editable = ('stage_index',)


@admin.register(models.Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'game', 'user', 'position', 'hand', 'is_host', 'bets')
    list_editable = ('position', 'is_host')


