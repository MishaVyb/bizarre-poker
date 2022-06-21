from django.contrib import admin
from games.models import Game, Player


class GameAdmin(admin.ModelAdmin):
    list_display = ('pk', 'deck', 'table', 'players_list')
    list_editable = ('deck', 'table')
    # search_fields = ('text',)
    # list_filter = ('created',)
    empty_value_display = '-empty-'


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('pk','user', 'game', 'hand')
    list_editable = ('hand',)

    empty_value_display = '-empty-'


admin.site.register(Game, GameAdmin)
admin.site.register(Player, PlayerAdmin)
