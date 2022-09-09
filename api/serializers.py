from typing import Any, Dict

from games.models import Game, Player, PlayerBet

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from games.services.stages import OpposingStage

from users.models import User
from django.db.models import Q
from core.functools.decorators import temporally
from games.backends.cards import Card

from rest_framework.request import Request

# class PlayerComboSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PlayerCombo
#         # fields = '__all__'
#         exclude = ('id',)


class PlayerBetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerBet
        fields = ('value',)


class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all()
    )
    game = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Game.objects.all()
    )
    bet_total = serializers.IntegerField(read_only=True)
    is_dealer = serializers.BooleanField(read_only=True)

    # def get_bet(self, obj: Player):
    #     return obj.bet._values

    # combo = PlayerComboSerializer(source='_combo', read_only=True)
    hand = serializers.SerializerMethodField()

    def get_hand(self, obj: Player):
        request: Request = self.context.get('request')
        user_players: list[Player] = request.user.players if request else []

        permition = any(
            [
                obj.game.stage == OpposingStage,  # show hand of all players at Opposing
                obj in user_players,  # show hand if it requested by owner
            ]
        )

        if permition:
            return str(obj.hand)
        else:
            with temporally(Card.Text, str_method='emoji_shirt'):
                return str(obj.hand)

    class Meta:
        model = Player
        fields = (
            'user',
            'game',
            'hand',
            'bet_total',
            'position',
            'is_host',
            'is_dealer',
            'is_active',
            #'combo',
        )
        extra_kwargs = {
            'is_dealer': {'read_only': True}
        }
        # validators = [
        #     UniqueTogetherValidator(
        #         message='User already playing this game',
        #         queryset=Player.objects.all(),
        #         fields=('user', 'game'),
        #     )
        # ]


class GameSerializer(serializers.ModelSerializer):
    players = serializers.StringRelatedField(
        many=True, read_only=True
    )
    players_detail = PlayerSerializer(many=True, source='players', read_only=True)

    stage = serializers.CharField(read_only=True)

    # pluser = serializers.SerializerMethodField()
    # other_players = serializers.SerializerMethodField()

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
            #'deck'
            #'deck_generator'
            'begins',
            # 'stage_index',
            'stage',  # ~ status
            'table',
            'bank',
            'players',
            'players_detail',
            #'pluser',
            #'other_players',
        )
