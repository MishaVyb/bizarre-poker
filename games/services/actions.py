import logging
from typing import Callable, Type

from core.functools.utils import StrColors, init_logger
from django.core.exceptions import ValidationError
from games.models import Game
from games.services.stages import (
    StagesContainer,
    BaseGameStage,
    BiddingsStage,
    PlacingBlindsStage,
    SetupStage,
)
from users.models import User

logger = init_logger(__name__, logging.INFO)


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
        self, game: Game, user: User, *args, act_immediately=True, **kwargs
    ) -> None:
        self.game = game
        self.user = user
        self.player = self.user.player_at(self.game)
        self.conditions = [
            BaseGameAction.stage_condition,
            BaseGameAction.performer_condition,
        ] + self.conditions

        if act_immediately:
            self.act()

    def __str__(self) -> str:
        return self.__class__.__name__

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BaseGameAction):
            return NotImplemented
        return (
            type(self) == type(__o) and self.game == __o.game and self.user == __o.user
        )

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
                reason = (
                    f'Condition {c.__name__} for acting {self} '
                    f'are not satisfied. {detail}'
                )
                raise ActError(f'Acting {self} failed. {reason}')

    def act(self):
        self.check_conditions()
        logger.info(f'{self.player} {StrColors.green("acting")} {self}')
        try:
            self.act_subclass()
        except ValidationError as e:
            raise ActError(f'Acting {self} failed. {e}')
        StagesContainer.continue_processing(self.game)

    def act_subclass(self):
        raise NotImplementedError


##############################################################################


class StartAction(BaseGameAction):
    suitable_stage = SetupStage
    conditions = [lambda action: action.player.is_host]

    def act_subclass(self):
        self.game.begins = True


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

        или наоборот может сделать новый вызов"""
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

    def act_subclass(self):
        # act
        self.user.profile.withdraw_money(self.value)
        self.user.player_at(self.game).bets.create(value=self.value)


class PlaceBlind(PlaceBet):
    suitable_stage = PlacingBlindsStage

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = game.stage.get_necessary_action_values().get('min')
        if value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
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
        value = game.stage.get_necessary_action_values().get('min')
        if value == 0:
            logger.warning(
                f'Acting {self} when there are not bets att all. '
                'Go ahead with value = 0, that equal to PlaceBetCheck. '
            )
        elif value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetVaBank(PlaceBet):
    """All in. Place max possible bet value."""

    def __init__(self, game: Game, user: User, *args, act_immediately=True, **kwargs):
        value = game.stage.get_necessary_action_values().get('max')
        if value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PassAction(BaseGameAction):
    suitable_stage = BiddingsStage

    def act_subclass(self):
        self.player.update(is_active=False)


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
        try:
            return next(filter(lambda x: x.__name__ == name, cls.actions))
        except StopIteration:
            raise ValueError(
                f'Invalid action name: {name}. '
                f'Available actions: {[a.__name__ for a in cls.actions]}'
            )
