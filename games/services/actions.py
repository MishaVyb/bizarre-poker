from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Generic, Type, TypeVar

from core.functools.utils import StrColors, init_logger
from core.types import NONE_ATTRIBUTE
from django.core.exceptions import ValidationError
from games.models import Game
from games.services.stages import (
    BaseGameStage,
    BiddingsStage,
    PlacingBlindsStage,
    SetupStage,
    StagesContainer,
)
from users.models import User

logger = init_logger(__name__)


class ActError(Exception):
    pass


class BaseGameAction:
    suitable_stage: type[BaseGameStage]
    conditions: list[Callable] = []
    error_messages: dict[str, str] = {
        'invalid_stage': (
            'Acting {self} failed. Game has another current stage: {stage}'
        ),
        'invalid_player': (
            'Acting {self} failed. '
            'Game waiting for act from another player: {performer}'
        ),
        'passive_player': (
            'Acting {self} failed. '
            'Player say `pass` and can not make game actions till next round. '
        ),
    }

    @property
    def error_messages_formated(self):
        formated = {}
        for k, v in self.error_messages.items():
            formated[k] = v.format(
                self=self, stage=self.game.stage, performer=self.game.stage.performer
            )
        return formated

    def __init__(
        self,
        game: Game,
        user: User,
        *args,
        act_immediately=True,
        processing_after_act=True,
        **kwargs,
    ) -> None:
        self.game = game
        self.user = user.player_at(game).user  # !!!!!!!!!!!!!
        self.player = user.player_at(game)  # player who made an action
        self.conditions = [
            BaseGameAction.stage_condition,
            BaseGameAction.performer_condition,
        ] + self.conditions

        if act_immediately:
            self.act(continue_processing_after=processing_after_act)

    def __repr__(self) -> str:
        player = self.player if hasattr(self, 'player') else '???'
        try:
            return f'{player} -> `{self.__class__.__name__}`'
        except Exception:
            return super().__repr__()

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BaseGameAction):
            return NotImplemented
        return (
            type(self) == type(__o) and self.game == __o.game and self.user == __o.user
        )

    @classmethod
    def preform(
        cls: Type[_ACTION_TYPE],
        user: User,
        stage: str | None = None,
        game: Game | None = None,
        **action_kwargs,
    ) -> ActionPreform[_ACTION_TYPE]:
        assert isinstance(
            user, User
        ), 'Wrong user type. Are you shure you are not confusing with __init__(..)'
        return ActionPreform(cls, user, stage, game, action_kwargs)

    def stage_condition(self):
        # we allow current stage to be a subclass of suitable stage
        # because we have BiddingStage-1 BiddingStage-2 etc, wich are subclasses
        current_stage = self.game.stage
        if not isinstance(current_stage, self.suitable_stage):
            raise ActError(self.error_messages_formated['invalid_stage'])
        return True

    def performer_condition(self):
        current_stage = self.game.stage
        if not self.player == current_stage.performer:
            raise ActError(self.error_messages_formated['invalid_player'])
        return True

    def check_conditions(self):
        for c in self.conditions:
            if not c(self):
                detail = self.error_messages.get(c.__name__) or ''
                reason = f'Condition {c.__name__} are not satisfied. {detail}'
                raise ActError(f'Acting {self} failed. {reason}')

    def act(self, *, continue_processing_after=True):
        # [1]
        self.check_conditions()
        # [2]
        logger.info(f'{StrColors.green("acting")} {self}')
        try:
            self.act_subclass()
        except ValidationError as e:
            raise ActError(f'Acting {self} failed. {e}')
        # [3]
        if continue_processing_after:
            StagesContainer.continue_processing(self.game)

    def act_subclass(self):
        raise NotImplementedError


_ACTION_TYPE = TypeVar('_ACTION_TYPE', bound=BaseGameAction)
_T = TypeVar('_T')


@dataclass
class ActionPreform(Generic[_ACTION_TYPE]):
    action_class: Type[_ACTION_TYPE]

    user: User
    'prepared for acting by user'

    stage: str | None = None  # key stage for action
    'prperate for actiong at stgae'

    game: Game | None = None
    action_kwargs: dict | None = None

    def __post_init__(self):
        if self.stage:
            try:
                StagesContainer.get(self.stage)
            except ValueError as e:
                raise ValueError(f'Invalid stage name for action preform: {e}')

    def act(self, game: Game | None = None, *, continue_processing_after=True):
        self.game = self.game or game
        assert self.game, 'Game should be provided'

        # check prefrom condition
        if self.stage and self.game.stage.name != self.stage:
            raise ActError(f'ActionPreform prepared for another stage: {self.stage}')
        self.action_class(
            self.game,
            self.user,
            act_immediately=True,
            processing_after_act=continue_processing_after,
            **self.action_kwargs or {},
        )

    def __eq__(self, other: object):
        if isinstance(other, ActionPreform):
            return asdict(self) == asdict(other)
        if isinstance(other, BaseGameAction):
            stage_eq = not self.stage or (self.stage == other.game.stage.name)
            game_eq = not self.game or (self.game == other.game)
            if self.action_kwargs:
                other_kwargs = {
                    k: getattr(other, k, NONE_ATTRIBUTE) for k in self.action_kwargs
                }
                kwargs_eq = self.action_kwargs == other_kwargs
            else:
                kwargs_eq = True

            return (
                self.action_class == type(other)
                and self.user == other.user
                and stage_eq
                and game_eq
                and kwargs_eq
            )
        return NotImplemented


########################################################################################
# Actions
########################################################################################


class StartAction(BaseGameAction):
    suitable_stage = SetupStage
    conditions = [lambda action: action.player.is_host]

    def act_subclass(self):
        self.game.begins = True
        self.game.presave()


class PlaceBet(BaseGameAction):
    suitable_stage = BiddingsStage

    def future_bet_total(self) -> int:
        return self.player.bet_total + self.value

    def value_in_valid_range_condition(self):
        necessary = self.game.stage.get_necessary_action_values()
        return necessary['min'] <= self.value <= necessary['max']

    def if_already_placed_bet_is_not_more_than_other_max_bet_condition(self):
        """если ставки уже сделаны и идет второй круг, то игрок может только
        удовлесторвить предыдущю ставку, но не поставить новый вызов

        или наоборот может сделать новый вызов

        сейчас максимальная ставка ограничего только значением 'max' в
        get_nessasery_value что равняется банку юзера (как вабанк)
        """
        return True

    conditions = [
        value_in_valid_range_condition,
        if_already_placed_bet_is_not_more_than_other_max_bet_condition,
    ]

    def __init__(
        self, game: Game, user: User, value: int, *args, act_immediately=True, **kwargs
    ):
        if value == 0 and type(self) == PlaceBet:
            logger.warning(
                f'Acting {self} with value = 0. '
                'Another action `PlaceBetCheck` for that value should be used. '
            )
        self.value = value
        super().__init__(game, user, act_immediately=act_immediately)

    def __repr__(self) -> str:
        try:
            return super().__repr__() + f' ${self.value}'
        except Exception:
            return super().__repr__()

    def act_subclass(self):
        # act
        self.user.profile.bank -= self.value
        self.user.profile.presave()
        self.player.bets.create(value=self.value)


class PlaceBlind(PlaceBet):
    suitable_stage = PlacingBlindsStage

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = self.suitable_stage(game).get_necessary_action_values().get('min')
        assert value is not None, 'invalid suitable stage'

        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetCheck(PlaceBet):
    """Player won`t place any bet.

    In that case we place 0 to mark that plyer made his desigion about bet.
    """

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = 0
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetReply(PlaceBet):
    """Reply to other player bet. Place min possible bet value."""

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = self.suitable_stage(game).get_necessary_action_values().get('min')
        assert value is not None, 'invalid suitable stage'

        if value == 0:
            logger.warning(
                f'Acting {self} when there are not bets att all. '
                'Go ahead with value = 0, that equal to PlaceBetCheck. '
            )
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetVaBank(PlaceBet):
    """All in. Place max possible bet value."""

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = self.suitable_stage(game).get_necessary_action_values().get('max')
        assert value is not None, 'invalid suitable stage'

        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PassAction(BaseGameAction):
    suitable_stage = BiddingsStage

    def act_subclass(self):
        self.player.is_active = False
        self.player.presave()


########################################################################################
# Action Contsiner
########################################################################################


class ActionContainer:
    actions: tuple[Type[BaseGameAction], ...] = (
        StartAction,
        PlaceBet,
        PlaceBlind,
        PlaceBetCheck,
        PlaceBetReply,
        PlaceBetVaBank,
        PassAction,
    )

    @classmethod
    def get(cls, name: str) -> Type[BaseGameAction]:
        if not name:
            raise ValueError('No name')

        try:
            return next(filter(lambda x: x.__name__ == name, cls.actions))
        except StopIteration:
            raise ValueError(
                f'Invalid action name: {name}. '
                f'Available actions: {[a.__name__ for a in cls.actions]}'
            )
