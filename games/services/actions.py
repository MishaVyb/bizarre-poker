"""

developing
[ ] если у другого игрока слишком маленький банк, что даже на блайнд не хватает
"""


import logging
from typing import Callable

from django.db import models
from core.functools.utils import init_logger

from core.functools.looptools import circle_after
from users.models import User
from ..models import Game, PlayerBet
from .stages import (
    PlacingBlindsStage,
    GAME_STAGES_LIST,
    BaseGameStage,
    BiddingsStage,
    SetupStage,
    StageProcessingError,
)
from django.core.exceptions import ValidationError

logger = init_logger(__name__, logging.INFO)


class ActError(Exception):
    pass


class BaseGameAction:
    suitable_stage: type[BaseGameStage]
    conditions: list[Callable] = []
    error_messages: dict[str, str] = {
        'invalid_stage': 'Acting {self} failed. Game has another current stage: {stage}',
        'invalid_player': 'Acting {self} failed. Game waiting for act from another player: {performer}',
        'passive_player': 'Acting {self} failed. Player say `pass` and can not make game actions till next round. ',
    }

    @property
    def error_messages_formated(self):
        formated = {}
        for k, v in self.error_messages.items():
            formated[k] = v.format(
                self=self, stage=self.game.stage, performer=self.game.stage.performer
            )
        return formated

    def __init__(self, game: Game, user: User, *, act_immediately=True) -> None:
        self.game = game
        self.user = user
        self.player = self.user.player_at(self.game)

        if act_immediately:
            self.act()

    def __str__(self) -> str:
        return self.__class__.__name__

    def base_conditions(self):
        # valid stage:
        current_stage = self.game.stage
        if not isinstance(current_stage, self.suitable_stage):
            raise ActError(self.error_messages_formated['invalid_stage'])
        # valid performer:
        elif not self.player == current_stage.performer:
            raise ActError(self.error_messages_formated['invalid_player'])
        # player is not passed
        if not self.player.is_active:
            raise ActError(self.error_messages_formated['passive_player'])

    def check_conditions(self):
        self.base_conditions()
        # sub class conditions:
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
        self.act_subclass()
        GAME_STAGES_LIST.continue_processing(self.game)

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

    # @property
    def future_bet_total(self) -> int:
        return self.player.bet_total + self.value

    def value_multiples_of_small_blind(self):
        # this validation is on field level but we catch it here before
        # othervise game will process with invalid bet value untill bet saving
        field: models.Field = PlayerBet.value.field
        try:
            field.run_validators(self.value)
        except ValidationError as e:
            return False
        return True

    def bet_equal_or_more_then_others(self):
        return self.future_bet_total() >= self.game.players.aggregate_max_bet()

    def player_has_enough_money(self):
        return self.value <= self.user.profile.bank

    def bet_is_not_more_then_others_banks(self):
        # проверим, что нет плееров, у которых оставшийся банк меньше, чем ставка
        q = self.game.players.active.filter(user__profile__bank__lt=self.value)
        return not q.exists()

    def if_already_placed_bet_is_not_more_than_other_max_bet(self):
        """если ставки уже сделаны и идет второй круг, то игрок может только
        удовлесторвить предыдущю ставку, но не поставить новый вызов

        или наоборот может сделать новый вызов"""
        return True

    conditions = [
        value_multiples_of_small_blind,
        player_has_enough_money,
        bet_equal_or_more_then_others,
        bet_is_not_more_then_others_banks,
        if_already_placed_bet_is_not_more_than_other_max_bet,
    ]

    def __init__(
        self, game: Game, user: User, value: int, *, act_immediately=True
    ) -> None:
        self.value = value
        super().__init__(game, user, act_immediately=act_immediately)

    def act_subclass(self):
        # act
        self.user.profile.withdraw_money(self.value)
        self.user.player_at(self.game).bets.create(value=self.value)


class PlaceBlind(PlaceBet):
    suitable_stage = PlacingBlindsStage  # type: ignore

    conditions = [
        PlaceBet.player_has_enough_money,
    ]

    def __init__(self, game: Game, user: User, *, act_immediately=True) -> None:
        value = game.stage.get_necessary_action_values().get('value')
        if value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetCheck(PlaceBet):
    """Player won`t place any bet.

    In that case we place 0 to mark that plyer made his desigion about bet.
    """

    def __init__(self, game: Game, user: User, *, act_immediately=True) -> None:
        value = 0
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetReply(PlaceBet):
    """Reply to other player bet. Place min possible bet value."""

    def __init__(self, game: Game, user: User, *, act_immediately=True) -> None:
        value = game.stage.get_necessary_action_values().get('min')
        if value is 0:
            logger.warning(
                'Acting PlaceBetReply when there are not bets att all. '
                'Go ahead with value = 0, that equal to PlaceBetCheck. '
            )
        elif value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PlaceBetVaBank(PlaceBet):
    """All in. Place max possible bet value."""

    def __init__(self, game: Game, user: User, *, act_immediately=True) -> None:
        value = game.stage.get_necessary_action_values().get('max')
        if value is None:
            self.game = game
            raise ActError(self.error_messages_formated['invalid_stage'])
        super().__init__(game, user, value=value, act_immediately=act_immediately)


class PassAction(BaseGameAction):
    suitable_stage = BiddingsStage

    def act_subclass(self):
        self.player.update(is_active=False)
