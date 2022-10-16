from rest_framework import serializers
from core.functools.utils import Interval

from games.models.game import Game
from games.services import actions


class PositiveInteger:
    message = 'Bet must be positive. '

    def __call__(self, value):
        if value < 0:
            raise serializers.ValidationError(self.message)

class MultipleOfSmallBlind:
    requires_context = True
    message = 'Bet must be a multiple of {blind}'

    def __call__(self, value, serializer: serializers.Serializer | serializers.Field):
        game: Game = serializer.context['game']
        blind = game.config.bet_multiplicity
        if value % blind != 0:
            raise serializers.ValidationError(self.message.format(blind=blind))

class InPossibleInterval:
    requires_context = True
    message = 'Bet must be in possible values interval {interval}'

    def __call__(self, value, serializer: serializers.Serializer | serializers.Field):
        game: Game = serializer.context['game']
        #action: Game = serializer.context['game']
        possible: Interval = game.stage.get_possible_values_for(actions.PlaceBet)
        if value not in possible:
            raise serializers.ValidationError(self.message.format(interval=possible))