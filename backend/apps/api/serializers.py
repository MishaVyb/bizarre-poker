from games.models import Game, Player
from games.models.player import PlayerPreform
from games.services.actions import ActionPrototype
from games.services.cards import Card, JokerCard
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import User

from apps.api import validators


class ActionSerializer(serializers.Serializer):
    available = serializers.BooleanField(default=True)
    url = serializers.SerializerMethodField()
    values = serializers.JSONField(source='action_values.dict', allow_null=True)

    def get_url(self, obj: ActionPrototype):
        url = self.context.get('action_url')
        game_pk = self.context.get('game_pk')
        assert url and game_pk, 'should be provided via serializer context'

        return url.format(game_pk=game_pk, name=obj.action_class.name)


class StageSerializer(serializers.Serializer):
    name = serializers.CharField(source='__repr__')
    performer = serializers.CharField()
    status = serializers.CharField(source='get_status_format')


class CardSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    suit = serializers.IntegerField()
    is_joker = serializers.BooleanField()
    kind = serializers.IntegerField(required=False)  # only Joker`s property
    is_mirror = serializers.SerializerMethodField()  # only Joker`s property
    string = serializers.CharField(source='get_str')

    def get_is_mirror(self, obj: Card):
        if isinstance(obj, JokerCard):
            return obj.is_mirror
        return None


class ComboSerializer(serializers.Serializer):
    kind = serializers.CharField()
    chain = CardSerializer(many=True, source='stacks.cases_chain')


class GameSerializer(serializers.ModelSerializer):
    players = serializers.StringRelatedField(
        many=True,
        read_only=True,
        source='players_manager',
    )
    table = CardSerializer(many=True, read_only=True)
    stage = StageSerializer(read_only=True)
    config = serializers.JSONField(source='config.dict', read_only=True)
    config_name = serializers.CharField(default='classic', write_only=True)

    class Meta:
        model = Game
        exclude = (
            'deck',
            'stage_index',
        )
        read_only_fields = [
            field.attname for field in Game._meta.fields if field.name != 'config_name'
        ]


class CurrentGameDefault:
    requires_context = True

    def __call__(self, field: serializers.Field) -> Game:
        return field.context['view'].get_game()


class PlayerSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username', queryset=User.objects.all()
    )
    game = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Game.objects.all(),
        default=CurrentGameDefault(),
    )
    hand = CardSerializer(many=True, read_only=True)
    combo = ComboSerializer(read_only=True)
    bets = serializers.JSONField(read_only=True, allow_null=True)
    bet_total = serializers.IntegerField(read_only=True)
    is_dealer = serializers.BooleanField(read_only=True)
    is_performer = serializers.BooleanField(read_only=True)
    profile_bank = serializers.IntegerField(source='user.profile.bank', read_only=True)

    class Meta:
        model = Player
        exclude = ('id', 'created', 'modified')
        extra_kwargs = {
            # position is requered for model but not for serializer
            # position is generated at model init_clean before saving
            'position': {'read_only': True},
        }
        validators = [
            UniqueTogetherValidator(
                queryset=Player.objects.all(),
                fields=['user', 'game'],
                message='User can play in Game only by one Player',
            )
        ]


class HiddenPlayerSerializer(PlayerSerializer):
    hand = serializers.SerializerMethodField()
    combo = serializers.SerializerMethodField()

    def get_hand(self, obj: Player):
        return [None] * len(obj.hand)

    def get_combo(self, obj: Player):
        return None


class BetValueSerializer(serializers.Serializer):
    value = serializers.IntegerField(
        validators=[
            validators.MultipleOfSmallBlind(),
            validators.PositiveInteger(),
            validators.InPossibleInterval(),
        ]
    )


class PlayerPreformSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault(),
    )
    game = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Game.objects.all(),
        default=CurrentGameDefault(),
    )

    class Meta:
        model = PlayerPreform
        exclude = ('id',)
        validators = [
            UniqueTogetherValidator(
                queryset=PlayerPreform.objects.all(),
                fields=['user', 'game'],
                message='User could not make many request to join a sigle game. ',
            )
        ]
