from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Generic, Literal, Type, TypeAlias, TypeVar

from core.functools.utils import Interval, init_logger
from core.validators import bet_multiplicity
from django.core.exceptions import ValidationError
from core.management.configurations import DEFAULT
from games.services.constraints import check_objects_continuity
from users.models import User

if TYPE_CHECKING:
    from games.models import Game
    from games.models.player import Player
    from games.services.stages import BaseStage

logger = init_logger(__name__)


_ACTION = TypeVar('_ACTION', bound='BaseAction')
'Bounded TypeVar for Generic functions that takes any subtype of BaseAction class. '
_AVP: TypeAlias = list[int] | Interval[int] | None
'Action values types at action prototype'


class ActionError(Exception):
    messages = {
        'not_available': (
            'Acitng failed. {action} not in game stage possible action prototypes. '
        ),
        'none_values': (
            'Acitng failed: got none values from stage. {action} not in game stage '
            'possible action prototypes or stage performer is None. Maybe Action '
            'Prototype should be used insted. '
        ),
    }

    def __init__(
        self,
        action: BaseAction,
        code: Literal['not_available', 'none_values'] = 'not_available',
    ) -> None:
        super().__init__(self.messages[code].format(action=action))


class BaseAction:
    message: str = '{player} did action'
    value: int  # type annotation for subclasses
    values_expected: ClassVar[bool] = False
    'Special class flag that stages could know is value neccessary for action or not'

    def get_message_format(self):
        return self.message.format(player=self.player)

    def __init__(self, game: Game, player: Player, **kwargs) -> None:
        check_objects_continuity(player, game.players)

        self.game = game
        self.player = player

    def __repr__(self) -> str:
        try:
            return f'{self.player} -> `{self.__class__.__name__}`'
        except Exception:
            return super().__repr__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseAction):
            return super().__eq__(other)
        return NotImplemented

    @classmethod
    def prototype(
        cls: Type[_ACTION],
        game: Game,
        player: Player,
        action_values: _AVP = None,
        suitable_stage_class: Type[BaseStage] | None = None,
    ) -> ActionPrototype[_ACTION]:
        return ActionPrototype(cls, game, player, action_values, suitable_stage_class)

    @classmethod
    def run(cls, game: Game, user: User, autosave=True, **action_kwargs):
        """Simple shortcut for running proccessor just after action added to it."""
        # at user instance from players, profile bank is prefetched, not at request user
        # therefore we use this trick to get player with prefethed fields
        # and we need player instance strictly form players selector from game instanse
        player = game.players.get(user=user)
        action = cls(game, player, **action_kwargs)
        processor = game.get_processor(autosave=autosave)
        processor.add(action)
        processor.run()

    def act(self):
        self.act_subclass()

    def act_subclass(self):
        raise NotImplementedError


@dataclass
class ActionPrototype(Generic[_ACTION]):
    action_class: Type[_ACTION]
    game: Game
    player: Player
    action_values: _AVP = None
    'action prototype with value in that range'
    suitable_stage_class: Type[BaseStage] | None = None
    'action prperared for acting at stgae (only for AutoProcessor handling)'

    def __post_init__(self):
        check_objects_continuity(self.player, self.game.players)

    def get_action(self, with_value: int | None = None):
        if with_value is not None:
            return self.action_class(self.game, self.player, value=with_value)
        return self.action_class(self.game, self.player)

    def __hash__(self) -> int:
        return hash(self.action_class)

    def __repr__(self) -> str:
        try:
            return f'({self.action_class.__name__}){self.action_values or ""}'
        except Exception:
            return super().__repr__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ActionPrototype):
            if not (self.action_class, self.game, self.player) == (
                other.action_class,
                other.game,
                other.player,
            ):
                return False
            if isinstance(self.action_values, type(other.action_values)):
                return self.action_values == other.action_values
            elif isinstance(self.action_values, Interval):
                return other.action_values in self.action_values
            else:
                return NotImplemented

        if not isinstance(other, BaseAction):
            return NotImplemented

        # Compare ActionPrototype with `real` Action:
        # [0] game_condition
        if self.game != other.game:
            return False
        check_objects_continuity(self.game, other.game)

        # [1] stage_condition (if specify at preform_action)
        if (
            self.suitable_stage_class
            and type(other.game.stage) != self.suitable_stage_class
        ):
            return False

        # [2] action_condition
        if not isinstance(other, self.action_class):
            return False

        # [3] performer_condition
        if self.player != other.player:
            return False
        check_objects_continuity(self.player, other.player)

        # [4] value_condition
        if other.values_expected:
            if self.action_values is None:
                return False

            if isinstance(self.action_values, list):
                if other.value not in self.action_values:
                    return False
            else:
                if other.value not in self.action_values:
                    return False

        elif self.action_values:
            return False

        return True


########################################################################################
# Actions
########################################################################################


class StartAction(BaseAction):
    message: str = '{player} make this game beggins'

    def act_subclass(self):
        self.game.begins = True
        self.game.presave()


class EndAction(BaseAction):
    message: str = '{player} make this game ends'

    def act_subclass(self):
        self.game.begins = False
        self.game.presave()


class PlaceBet(BaseAction):
    message: str = '{player} place bet {value:.2f}'
    values_expected = True

    def get_message_format(self):
        return self.message.format(player=self.player.user, value=self.value / 100)

    def __init__(self, game: Game, player: Player, value: int):
        try:
            bet_multiplicity(value)
        except ValidationError as e:
            raise ActionError(e)

        self.value = value
        super().__init__(game, player)

    def __repr__(self) -> str:
        value = f' ${self.value}' if hasattr(self, 'value') else ''
        return super().__repr__() + value

    def act_subclass(self):
        # act
        self.player.user.profile.bank -= self.value
        self.player.user.profile.presave()
        self.player.bets.append(self.value)
        self.player.presave()


class PlaceBlind(PlaceBet):
    message: str = '{player} place {blind} blind'
    values_expected = False

    def get_message_format(self):
        return self.message.format(
            player=self.player.user,
            blind='small' if self.value == DEFAULT.small_blind else 'big',
        )

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        values = game.stage.get_possible_values_for(self)
        if not values or not isinstance(values, list):
            raise ActionError(self, 'none_values')

        if len(values) != 1:
            raise ValueError('Values provides not sigle value. ')

        self.value = values[0]


class PlaceBetCheck(PlaceBet):
    """Player won`t place any bet.

    In that case we place 0 to mark that plyer made his desigion about bet.
    """

    message: str = '{player} says check'
    values_expected = False

    def __init__(self, game: Game, player: Player):
        value = 0
        super().__init__(game, player, value=value)


class PlaceBetReply(PlaceBet):
    """Reply to other player bet. Place min possible bet value."""

    values_expected = False

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        values = game.stage.get_possible_values_for(self)
        if not values or not isinstance(values, Interval):
            raise ActionError(self, 'none_values')

        if values.min == 0:
            raise ValueError(f'{self} with 0 when there are no other bet was placed. ')
        super().__init__(game, player, value=values.min)


class PlaceBetVaBank(PlaceBet):
    """All in. Place max possible bet value."""

    message: str = '{player} placed all in (vabank)'
    values_expected = False

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        values = game.stage.get_possible_values_for(self)
        if not values or not isinstance(values, Interval):
            raise ActionError(self, 'none_values')

        super().__init__(game, player, value=values.max)


class PassAction(BaseAction):
    message: str = '{player} says pass'

    def act_subclass(self):
        self.player.is_active = False
        self.player.presave()
