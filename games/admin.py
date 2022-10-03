from django.contrib import admin

from games import models


@admin.register(models.PlayerBet)
class DefaultAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('pk', 'stage_index', 'deck', 'table', 'players')
    list_editable = ('stage_index',)
    # search_fields = ('text',)
    # list_filter = ('created',)
    empty_value_display = 'empty'


@admin.register(models.Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'game', 'user', 'position', 'hand', 'is_host')
    list_editable = ('position', 'is_host')

    empty_value_display = 'empty'
