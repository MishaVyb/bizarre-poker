from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Generic,
    Literal,
    Sequence,
    Type,
    TypeAlias,
    TypeVar,
)

from core.utils import Interval, init_logger

from games.services.constraints import check_objects_continuity
from users.models import User

if TYPE_CHECKING:
    from games.models import Game
    from games.models.player import Player
    from games.services.stages import BaseStage

    _ActionValuesTypes: TypeAlias = int | Interval[int] | Sequence[Player] | Player

logger = init_logger(__name__)

_ACTION = TypeVar('_ACTION', bound='BaseAction')
'Bounded TypeVar for Generic functions that takes any subtype of BaseAction class. '


class ActionError(Exception):
    messages = {
        'not_available': (
            'Acitng failed. {action} not in game stage possible action prototypes. '
        ),
        'invalid_values': (
            'Acitng failed: got none values or invalid value type. If you are only '
            'preparing action to be performed later, Action Prototype should be used '
            'instead. '
        ),
    }

    def __init__(
        self,
        action: BaseAction,
        code: Literal['not_available', 'invalid_values'] = 'not_available',
    ) -> None:
        self.action = action
        super().__init__(self.messages[code].format(action=action))


class BaseAction:
    value: int | Player
    'Action value: int for PlaceBet, Player for KickOut'
    values_expected: ClassVar[bool] = False
    'Special class flag that stages could know is value neccessary for action or not'

    name = 'action'
    message: str = '{player} did action'

    def get_message_format(self):
        return self.message.format(player=self.player)

    def __init__(self, game: Game, player: Player) -> None:
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
        user: User | Player,
        action_values: _ActionValuesTypes | None = None,
        suitable_stage_class: Type[BaseStage] | None = None,
    ) -> ActionPrototype[_ACTION]:
        if isinstance(user, User):
            player = game.players.get(user=user)
        else:
            player = user  # user is a Player instance in that case
        return ActionPrototype(cls, game, player, action_values, suitable_stage_class)

    @classmethod
    def run(
        cls,
        game: Game,
        user: User | Player | None = None,
        autosave=True,
        **action_kwargs,
    ):
        """
        Simple shortcut for running proccessor just after action added to it.
        If `user` is not provided, `performer` will be taken.
        """
        if isinstance(user, User):
            # at user instance from players, profile bank is prefetched, not at request
            # user therefore we use this trick to get player with prefethed fields and
            # we need player instance strictly form players selector from game instanse
            player = game.players.get(user=user)
        elif user is None:
            player = game.stage.performer
        else:
            player = user  # user is a Player instance in that case

        if not player:
            raise ValueError('None player provided for running action. ')

        action = cls(game, player, **action_kwargs)
        processor = game.get_processor(autosave=autosave)
        processor.add(action)
        processor.run()

    def act(self):
        raise NotImplementedError


@dataclass
class ActionPrototype(Generic[_ACTION]):
    action_class: Type[_ACTION]
    game: Game
    player: Player
    action_values: _ActionValuesTypes | None = None
    'action preppared with value in Interval range or with certain value'
    suitable_stage_class: Type[BaseStage] | None = None
    'action prperared for acting at stgae (only for AutoProcessor handling)'

    def __post_init__(self):
        check_objects_continuity(self.player, self.game.players)

    def get_action(self, *, use_value: Literal['min', 'max'] | None = None):
        """
        Create and get action from self prepared data.
        `action_values` should be provided as single value, not Interval.
        """
        action_kwargs: dict[str, int] = {}
        if self.action_values:
            if isinstance(self.action_values, Interval):
                assert use_value, 'use_value should be provided for multy values'
                action_kwargs['value'] = getattr(self.action_values, use_value)
            elif isinstance(self.action_values, int):
                assert not use_value, 'use_value makes no sense fot single value'
                action_kwargs['value'] = self.action_values
            else:
                raise TypeError(
                    f'Invalid action_values type: {type(self.action_values)}'
                )

        return self.action_class(self.game, self.player, **action_kwargs)

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
            elif isinstance(self.action_values, Interval) and isinstance(
                other.action_values, int
            ):
                return other.action_values in self.action_values

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

            if isinstance(self.action_values, Interval):
                return other.value in self.action_values
            elif isinstance(self.action_values, Sequence):
                return other.value in self.action_values
            else:
                return other.value == self.action_values
        elif self.action_values:
            return False

        return True


########################################################################################
# Actions
########################################################################################


class StartAction(BaseAction):
    name = 'start'
    message: str = '{player} make this game beggins'

    def act(self):
        self.game.begins = True
        self.game.presave()


class EndAction(BaseAction):
    name = 'end'
    message: str = '{player} make this game ends'

    def act(self):
        self.game.begins = False
        self.game.presave()


class ForceContinueAction(BaseAction):
    name = 'forceContinue'
    message: str = '{player} forcing game continue'
    # [TODO]
    # Move from AutoProcessing to that seperate Action


class LeaveGame(BaseAction):
    name = 'leaving'
    message: str = '{player} leaves game'

    def act(self):
        self.destroy(self.player)

    def destroy(self, leaver: Player):
        # exclude self from game players selector
        self.game.select_players(leaver.other_players)

        # change player positions for new selector
        for i, player in enumerate(self.game.players):
            player.position = i
            player.presave()

        # transfer all bets to game bank
        self.game.bank += leaver.bet_total
        self.game.presave()

        # perform destroy
        leaver.delete()


class KickOut(LeaveGame):
    name = 'kick'
    message: str = '{player} kicks out {kicker}'
    values_expected = True
    value: Player

    def __init__(self, game: Game, player: Player, value: Player) -> None:
        self.value = value
        super().__init__(game, player)

    def act(self):
        self.destroy(self.value)

    def get_message_format(self):
        return self.message.format(player=self.player.user, kicker=self.value)


########################################################################################
# Biddings Actions
########################################################################################


class PassAction(BaseAction):
    name = 'pass'
    message: str = '{player} says pass'

    def act(self):
        self.player.is_active = False
        self.player.presave()


class PlaceBet(BaseAction):
    name = 'bet'
    message: str = '{player} place bet {value:.2f}'
    values_expected = True
    value: int

    def get_message_format(self):
        return self.message.format(player=self.player.user, value=self.value)

    def __init__(self, game: Game, player: Player, value: int):
        self.value = value
        super().__init__(game, player)

    def __repr__(self) -> str:
        value = f' ${self.value}' if hasattr(self, 'value') else ''
        return super().__repr__() + value

    def act(self):
        # act
        self.player.user.profile.bank -= self.value
        self.player.user.profile.presave()
        self.player.bets.append(self.value)
        self.player.presave()


class PlaceBlind(PlaceBet):
    name = 'blind'
    message: str = '{player} place {blind} blind'
    values_expected = False

    def get_message_format(self):
        return self.message.format(
            player=self.player.user,
            blind='small' if self.value == self.game.config.small_blind else 'big',
        )

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        value = game.stage.get_possible_values_for(self)
        if not isinstance(value, int):
            raise ActionError(self, 'invalid_values')

        self.value = value


class PlaceBetCheck(PlaceBet):
    """Player won`t place any bet.

    In that case we place 0 to mark that plyer made his desigion about bet.
    """

    name = 'check'
    message: str = '{player} says check'
    values_expected = False

    def __init__(self, game: Game, player: Player):
        value = 0
        super().__init__(game, player, value=value)


class PlaceBetReply(PlaceBet):
    """Reply to other player bet. Place min possible bet value."""

    name = 'reply'
    message: str = '{player} reply to bet'
    values_expected = False

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        values = game.stage.get_possible_values_for(self)
        if not values or not isinstance(values, Interval):
            raise ActionError(self, 'invalid_values')

        if values.min == 0:
            raise ValueError(f'{self} with 0 when there are no other bet was placed. ')
        super().__init__(game, player, value=values.min)


class PlaceBetVaBank(PlaceBet):
    """All in. Place max possible bet value."""

    name = 'vabank'
    message: str = '{player} placed all in (vabank)'
    values_expected = False

    def __init__(self, game: Game, player: Player):
        super(PlaceBet, self).__init__(game, player)

        values = game.stage.get_possible_values_for(self)
        if not isinstance(values, Interval):
            raise ActionError(self, 'invalid_values')

        super().__init__(game, player, value=values.max)
