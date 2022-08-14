from django.contrib import admin

from games import models


@admin.register(models.PlayerBet, models.PlayerCombo)
class DefaultAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('pk', 'action_name', 'deck', 'table', 'players')
    list_editable = ('action_name',)
    # search_fields = ('text',)
    # list_filter = ('created',)
    empty_value_display = 'empty'


@admin.register(models.Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'hand', 'dealer', 'host')
    list_editable = ('dealer', 'host')

    empty_value_display = 'empty'
