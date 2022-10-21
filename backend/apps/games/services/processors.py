from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Type

from core.utils import StrColors, init_logger
from games.services import stages
from games.services import actions
from games.services.actions import ActionError, ActionPrototype, BaseAction
from games.services.constraints import check_objects_continuity, validate_constraints
from games.services.stages import BaseStage, RequirementNotSatisfied


if TYPE_CHECKING:
    from games.models.game import Game

logger = init_logger(__name__)


@dataclass
class ProcessingStatus:
    status_code: int


class PrematureFinalCondition:
    code = ''
    message = ''

    def __call__(self, game: Game) -> bool:
        return False


class AllOtherPassedCondition(PrematureFinalCondition):
    code = 'all_passed'
    message = 'all other player passed'

    def __call__(self, game: Game):
        return len(list(game.players.active)) == 1


class NoneBiddingsCondition(PrematureFinalCondition):
    code = 'none_biddings'
    message = 'bidding for nothing, only place bet check is allowed'

    def __call__(self, game: Game):
        performer = game.stage.performer
        if performer:
            check_action = actions.PlaceBetCheck.prototype(game, performer)
            return game.stage.get_possible_actions() == [check_action]
        return False


class BaseProcessor:
    actions_stack: list[BaseAction]

    STOP = ProcessingStatus(100)
    FORCED_STOP = ProcessingStatus(101)
    CONTINUE = ProcessingStatus(300)
    NEW_ROUND = ProcessingStatus(301)

    def __init__(self, game: Game, *, autosave: bool = True) -> None:
        self.game = game
        self.actions_stack = []
        self.autosave = autosave

    def add(self, action: BaseAction):
        check_objects_continuity(self.game, action.game)
        self.actions_stack.append(action)
        return self

    def run(self) -> ProcessingStatus:
        status = self._subrunner()
        if self.autosave:
            self._save_game_objects(status)
        return status

    def _subrunner(self) -> ProcessingStatus:
        if self._round_counter() == self.FORCED_STOP:
            return self.FORCED_STOP

        headline = StrColors.bold('Processing')
        logger.info(f'{headline} {self.game}. ')

        # [NOTE]
        # we are getting current stage from Game only once to cache their properties
        # when stage complited run(..) will be called again and we ask for stage again
        current_stage = self.game.stage

        # [01] actions
        if self._actions_processing(current_stage) == self.FORCED_STOP:
            return self.FORCED_STOP

        # [02] stages
        status = self._stage_processing(current_stage)
        if status in [self.STOP, self.FORCED_STOP]:
            return status

        return self._subrunner()

    def _actions_processing(self, current_stage: BaseStage):
        # [NOTE]
        # No catching rasies here: if processor contains invalid actions - it's failed.
        # The logic that we dont want give to user even an possobility to make invalid
        # action
        while self.actions_stack:
            action = self.actions_stack.pop()

            possible = current_stage.get_possible_actions()
            if action in possible:
                logger.info(' '.join([StrColors.green('acting'), str(action)]))
                action.act()
                self._make_history(action)
            else:
                # no possible found for that action (processor contains invalid action)
                raise ActionError(action)

    def _stage_processing(self, current_stage: BaseStage):
        premature_final = self._premature_final_condition(current_stage)

        # [NOTE]
        # But cacthing rases here. If requirement unsatisfied, it is totally okey.
        # We just try to be sure. Stop processing and make response in that case.
        try:
            current_stage.check_requirements()
        except RequirementNotSatisfied as e:
            # if premature finale we proceed farter to Opposing Stage
            if not premature_final:
                logger.info(e)
                self.game.presave()
                return self.STOP

        logger.info(f'{StrColors.cyan("exicuting")} {str(current_stage)}')
        current_stage.execute()
        logger.info(
            f'Game stage complited: {current_stage.get_message_format()}. '
            f'{StrColors.green("Continue")}. '
        )

        # stage compited successfully!
        self._make_history(current_stage)
        if premature_final:
            self._continue_to_final()
        else:
            self._continue_to_next_stage()

        return self.CONTINUE

    def _save_game_objects(self, status: ProcessingStatus):
        """
        Saving game, players, and users banks. Only if presave flag is True.
        """
        skip = ['performer'] if status == self.FORCED_STOP else []
        validate_constraints(self.game, skip=skip)
        self.game.save(only_if_presave=True)
        for player in self.game.players:
            player.save(only_if_presave=True)
            player.user.profile.save(only_if_presave=True)

    def _make_history(self, latest: BaseStage | BaseAction):
        performer = getattr(latest, 'player', None)
        value = getattr(latest, 'value', None)
        self.game.actions_history.append(
            {
                'class': latest.__class__.__name__,
                'performer': str(performer) if performer else None,
                'message': latest.get_message_format(),
                'value': value,
            }
        )

    def _round_counter(self):
        if self.game.stage == stages.SetupStage:
            # self.game.rounds_counter += 1
            logger.info(f'-- Game round #{self.game.rounds_counter} --')
            # self.game.presave()
            return self.NEW_ROUND
        return self.CONTINUE

    def _premature_final_condition(self, current_stage: BaseStage):
        """Any condition to proceed to the final stage skip others."""
        try:
            opposing_index = self.game.stages.index(stages.OpposingStage)
        except ValueError:
            # [FIXME]
            # in that case game has no opposing stage we mast proceed to TearDownStage
            # tmp solution:
            return False

        if current_stage == stages.SetupStage:
            return False  # game not started yet
        if self.game.stage_index >= opposing_index:
            return False  # alerady at final stages

        conditions: list[PrematureFinalCondition] = [
            AllOtherPassedCondition(),
            NoneBiddingsCondition(),
        ]
        for condition in conditions:
            if condition(self.game):
                logger.info(
                    f'Premature final condition {condition.code} satisfied: '
                    f'{condition.message}. Opposing Stage will be exicuted after. '
                )
                return True

        return False

    def _continue_to_next_stage(self):
        if self.game.stage_index + 1 < len(self.game.stages):
            self.game.stage_index += 1
        else:
            self.game.stage_index = 0
        self.game.presave()

    def _continue_to_final(self):
        """Proceed to `OpposingStage`."""
        opposing_index = self.game.stages.index(stages.OpposingStage)
        self.game.stage_index = opposing_index
        self.game.presave()


class AutoProcessor(BaseProcessor):
    def __init__(
        self,
        game: Game,
        *,
        with_actions: list[ActionPrototype] = [],
        stop_before_stage: Type[BaseStage] = None,
        stop_after_stage: Type[BaseStage] = None,
        stop_before_action: ActionPrototype | None = None,
        stop_after_action: ActionPrototype | None = None,
        stop_after_rounds_amount: int | None = None,
        stop_after_actions_amount: int | None = None,
        autosave: bool = True,
    ):
        super().__init__(game, autosave=autosave)

        supported_keys = [
            'stop_before_stage',
            'stop_after_stage',
            'stop_before_action',
            'stop_after_action',
            'stop_after_rounds_amount',
            'stop_after_actions_amount',
        ]
        kwargs = locals()
        params: dict[str, Any] = {
            arg: kwargs[arg] for arg in supported_keys if kwargs[arg]
        }

        if not params and with_actions:
            params['stop_after_with_actions'] = True

        assert params, 'No stop condition provided. '
        assert len(params) == 1, f'Many condition provided, expect only one: {params}'

        self.stop_factor = params
        self.stop_name = next(iter(params))

        if 'stage' in self.stop_name:
            stage = next(iter(self.stop_factor.values()))
            assert stage in self.game.stages, 'That stage not in this game. '

        self.with_actions = with_actions
        self.actions_counter = 0

        stop_amount: int = self.stop_factor.get('stop_after_rounds_amount', 0)
        if stop_amount:
            self.game_rounds_amount = stop_amount  # by stop condition
        else:
            self.game_rounds_amount = len(self.game.players)  # by deafult

    def run(self) -> ProcessingStatus:
        _ = 'AutoProcessor running. '
        logger.info(
            StrColors.purple(_)
            + f'Stop factor: {self.stop_factor}. '
            + f'With actions: {self.with_actions}'
        )

        status = super().run()

        if self.with_actions:
            raise RuntimeError(
                f'Reach stop factor: {self.stop_name} | {self.stop_factor}, '
                'but not all `with_actions` have been acted. '
            )

        logger.info(StrColors.purple('[AutoProcessor has stoped]'))
        return status

    def _round_counter(self):
        if super()._round_counter() == self.NEW_ROUND:
            if self.game.rounds_counter > self.game_rounds_amount:
                if self.stop_name == 'stop_after_rounds_amount':
                    return self.FORCED_STOP

                raise RuntimeError(
                    'Too many game round iterations. It makes no sense. '
                    'Probably autoplaying will never reach stop factor: '
                    f'{self.stop_name} | {self.stop_factor}. '
                    'Check attributes provided to AutoProcessor(..). '
                )
        return self.CONTINUE

    def _stop_after_action_condition(self, acted_proto: ActionPrototype):
        self.actions_counter += 1
        stop = self.stop_factor.get('stop_after_actions_amount')
        if stop and stop <= self.actions_counter:
            return self.FORCED_STOP

        if self.stop_factor.get('stop_after_action') == acted_proto:  # action
            return self.FORCED_STOP

        if self.stop_factor.get('stop_after_with_actions') and not self.with_actions:
            return self.FORCED_STOP

        return self.CONTINUE

    def _actions_processing(self, current_stage: BaseStage):
        # [1] try all with_actions:
        for proto in self.with_actions.copy():  # copy: because of removing items
            if proto.suitable_stage_class:
                if current_stage != proto.suitable_stage_class:
                    continue

            try:
                self.add(proto.get_action())
                super()._actions_processing(current_stage)
            except ActionError:
                continue  # okey, try later
            finally:
                self.actions_stack.clear()

            self.with_actions.remove(proto)
            if self._stop_after_action_condition(proto) == self.FORCED_STOP:
                return self.FORCED_STOP

        # [2] append new auto generated action
        # [2.1] take first possible action prototype
        protos = current_stage.get_possible_actions()
        if not protos:
            return self.CONTINUE
        proto = protos[0]

        if self.stop_factor.get('stop_before_action') == proto:
            return self.FORCED_STOP

        # [2.2] add action with first possible value
        self.add(proto.get_action(use_value='min'))
        super()._actions_processing(current_stage)

        if self._stop_after_action_condition(proto) == self.FORCED_STOP:
            return self.FORCED_STOP

        # [2.3] making auto actions untill stage requirement will be satisfied
        if not current_stage.check_requirements(raises=False):
            return self._actions_processing(current_stage)

        return self.CONTINUE

    def _stage_processing(self, current_stage: BaseStage):
        if self.stop_factor.get('stop_before_stage') == current_stage:
            return self.FORCED_STOP

        status = super()._stage_processing(current_stage)

        if self.stop_factor.get('stop_after_stage') == current_stage:
            return self.FORCED_STOP

        # [NOTE]
        # second check for stop_before_stage: when stage has been complited (CONTINUE)
        # stage_index goes to next stage and we need to re-check if this stage is stop
        # factor. if yes, we need to interrupt processing to prevent auto acting actions
        # at this new stage.
        if status == self.CONTINUE:
            if self.stop_factor.get('stop_before_stage') == self.game.stage:
                return self.FORCED_STOP

        return status
