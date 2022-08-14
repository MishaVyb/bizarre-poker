from typing import Any, Dict

from games.models import Game, Player, PlayerBet, PlayerCombo, RequirementError
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from games.models.game import Opposing
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
        fields = ('value',)
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
        return obj.bet.value

    combo = PlayerComboSerializer(source='_combo', read_only=True)
    hand = serializers.SerializerMethodField()

    def get_hand(self, obj: Player):

        # show hand of all players at Opposing
        if obj.game.current_action == Opposing:
            return str(obj.hand)

        request: Request = self.context.get('request')
        if request is None:
            with temporally(Card.Text, str_method='emoji_shirt'):
                hidden = str(obj.hand)
            return hidden

        if obj in request.user.players:
            return str(obj.hand)

        with temporally(Card.Text, str_method='emoji_shirt'):
            hidden = str(obj.hand)
        return hidden

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

    pluser = serializers.SerializerMethodField()
    other_players = serializers.SerializerMethodField()

    def get_pluser(self, obj: Game):
        request: Request = self.context.get('request')
        if request is None:
            return []

        pluser = request.user.players.get(game=obj)
        return PlayerSerializer(instance=pluser).data

    def get_other_players(self, obj: Game):
        request: Request = self.context.get('request')
        if request is None:
            return []


        other_players = obj.players.filter(~Q(user=request.user))
        return PlayerSerializer(other_players, many=True).data


    class Meta:
        model = Game
        fields = (
            'id',
            'action_name',
            'status',
            'table',
            'bank',
            'players',
            'pluser',
            'other_players',
            'players_detail',
        )
        # read_only_fields = 'players'
        # exclude = ('id', 'created', 'modified', 'deck_generator')
