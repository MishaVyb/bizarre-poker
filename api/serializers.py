from typing import Any, Dict

from games.models import Game, Player, PlayerBet, PlayerCombo

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from users.models import User
from django.db.models import Q
from core.functools.decorators import temporally
from games.backends.cards import Card

from rest_framework.request import Request

class PlayerComboSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerCombo
        # fields = '__all__'
        exclude = ('id',)


class PlayerBetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerBet
        fields = ('_values',)
        # exclude = ('id','created', 'modified')


class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all()
    )
    game = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Game.objects.all()
    )
    bet = serializers.SerializerMethodField()

    def get_bet(self, obj: Player):
        return obj.bet._values

    combo = PlayerComboSerializer(source='_combo', read_only=True)
    hand = serializers.SerializerMethodField()

    def get_hand(self, obj: Player):
        request: Request = self.context.get('request')
        user_players: list[Player] = request.user.players if request else []

        permition = any([
            obj.game.current_action == Opposing,  # show hand of all players at Opposing
            obj in user_players                   # show hand if it requested by owner
        ])

        if permition:
            return str(obj.hand)
        else:
            with temporally(Card.Text, str_method='emoji_shirt'):
                return str(obj.hand)


    class Meta:
        model = Player
        fields = ('user', 'game', 'position', 'host', 'dealer', 'bet', 'hand', 'combo')
        validators = [
            UniqueTogetherValidator(
                message='User already playing this game',
                queryset=Player.objects.all(),
                fields=('user', 'game'),
            )
        ]
        # exclude = ('id', 'created', 'modified', 'game')


class GameSerializer(serializers.ModelSerializer):
    players = serializers.StringRelatedField(
        many=True, source='_players', read_only=True
    )
    players_detail = PlayerSerializer(many=True, source='_players', read_only=True)

    status = serializers.SerializerMethodField()

    def get_status(self, obj: Game):
        try:
            obj.continue_processing()
        except RequirementError as e:
            return str(e)

    #pluser = serializers.SerializerMethodField()
    #other_players = serializers.SerializerMethodField()

    # def get_pluser(self, obj: Game):
    #     request: Request = self.context.get('request')
    #     if request is None:
    #         return []

    #     pluser = request.user.players.get(game=obj)
    #     serializer = PlayerSerializer(instance=pluser, context=self.context)
    #     return serializer.data

    # def get_other_players(self, obj: Game):
    #     request: Request = self.context.get('request')
    #     if request is None:
    #         return []

    #     other_players = obj.players.filter(~Q(user=request.user))

    #     serializer = PlayerSerializer(other_players, many=True, context=self.context)
    #     return serializer.data


    class Meta:
        model = Game
        fields = (
            'id',
            'action_name',
            'status',
            'table',
            'bank',
            'players',
            #'pluser',
            #'other_players',
            'players_detail',
        )
