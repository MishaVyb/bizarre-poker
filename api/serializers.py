from games.models import Game, Player

from rest_framework import serializers
from games.services import stages

from users.models import User
from games.services.cards import CardList

from rest_framework.request import Request


class StageSeroalizer(serializers.Serializer):
    # verbose_name = serializers.CharField()
    performer = serializers.CharField()


class GameSerializer(serializers.ModelSerializer):
    players = serializers.StringRelatedField(
        many=True,
        read_only=True,
        source='players_manager',
    )
    deck = serializers.SerializerMethodField()
    table = serializers.CharField(read_only=True)
    stage = StageSeroalizer(read_only=True)

    def get_deck(self, obj: Game):
        return obj.deck.hiden()  # always hiden

    class Meta:
        model = Game
        fields = (
            'id',
            'deck',
            'begins',
            'stage_index',
            'stage',
            'rounds_counter',
            'table',
            'bank',
            'players',
            'status',
            'actions_history',
        )


class ComboSerializer(serializers.Serializer):
    kind = serializers.StringRelatedField()

    class Meta:
        fields = ('kind',)


class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all()
    )
    game = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Game.objects.all()
    )
    #bets = serializers.BooleanField(read_only=True, allow_null=True)
    bet_total = serializers.IntegerField(read_only=True)
    is_dealer = serializers.BooleanField(read_only=True)
    hand = serializers.SerializerMethodField()
    profile_bank = serializers.SerializerMethodField()
    combo = serializers.SerializerMethodField()
    is_performer = serializers.SerializerMethodField()

    def permition(self, obj: Player):
        """player hand and combo visability permitions"""
        request: Request = self.context.get('request')
        assert request, 'you should pass request trhough context'

        user_players: list[Player] = request.user.players
        permition = [
            # [1] show hand of all players at Opposing or TearDownStage
            obj.game.stage in [stages.OpposingStage, stages.TearDownStage],
            # [2] or show hand if it requested by owner
            obj in user_players,
        ]
        return any(permition)

    def get_hand(self, obj: Player):
        if self.permition(obj):
            return str(obj.hand)
        return obj.hand.hiden()

    def get_profile_bank(self, obj: Player):
        return obj.user.profile.bank

    def get_combo(self, obj: Player):
        if self.permition(obj):
            combo = obj.combo
            if not combo:
                return {}
            return {
                'name': combo.kind.name,
                'stacks': str(CardList(instance=combo.stacks.cases_chain)),
            }

    def get_is_performer(self, obj: Player):
        return obj == obj.game.stage.performer

    class Meta:
        model = Player
        fields = (
            'user',
            'game',
            'hand',
            'bet_total',
            'bet_is_placed',  # exist or not
            'position',
            'is_host',
            'is_dealer',
            'is_active',
            'is_performer',
            'profile_bank',
            'combo',
        )
        extra_kwargs = {'is_dealer': {'read_only': True}}


class BetValueSerializer(serializers.Serializer):
    value = serializers.IntegerField()
