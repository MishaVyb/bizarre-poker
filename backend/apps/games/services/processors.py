from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Type

from core.functools.utils import StrColors, init_logger
from games.services import stages
from games.services.actions import ActionError, ActionPrototype, BaseAction
from games.services.constraints import check_objects_continuity, validate_constraints
from games.services.stages import BaseStage, RequirementNotSatisfied


if TYPE_CHECKING:
    from games.models.game import Game

logger = init_logger(__name__)


@dataclass
class ProcessingStatus:
    status_code: int


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

    def _make_history(self, latest: BaseStage | BaseAction):
        if isinstance(latest, BaseAction):
            self.game.actions_history.append(
                {
                    'performer': str(latest.player),
                    'class': str(type(latest)),
                    'message': latest.get_message_format(),
                }
            )
        else:
            message = latest.get_message_format()
            if message:
                self.game.actions_history.append(
                    {
                        'performer': None,  # None for stage maded by game processing
                        'class': str(latest),
                        'message': message,
                    }
                )

    def _actions_processing(self, current_stage: BaseStage):
        # [1]
        # No catching rasies here: if processor contains invalid actions - it's failed.
        # The logic that we dont want give even an possobility to user make an invalid
        # action

        # перебираем весь стэк с экшинами и сравниваем со всеми возможными дейсвтиями
        # из возможных действий
        # ессли экшен в стеке -- его обязательно нужно выполнить, иначе рейзим ощибку

        while self.actions_stack:
            action = self.actions_stack.pop()

            possible = current_stage.get_possible_actions()
            if action in possible:
                logger.info(' '.join([StrColors.green('acting'), str(action)]))
                action.act()
                self._make_history(action)
            else:
                raise ActionError(action)  # NO POSSIBLE FOUND FOR THAT ACTION...

    def _stage_processing(self, current_stage: BaseStage):
        # [2]
        # But cacthing rases here.
        # If requirement unsatisfied, it is totally okey (we just try to be sure),
        # stop processing and make response in that case.
        try:
            current_stage.check_requirements()
        except RequirementNotSatisfied as e:
            logger.info(e)
            status = current_stage.message_requirement_unsatisfied
            self.game.status = status.format(player=current_stage.performer)
            self.game.presave()
            return self.STOP

        logger.info(' '.join([StrColors.cyan('exicuting'), str(current_stage)]))
        current_stage.execute()

        # stage compited successfully!
        self._stage_complited(current_stage)
        logger.info(f'Game stage complited. {StrColors.green("Continue")}.')

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

    def add(self, action: BaseAction):
        check_objects_continuity(self.game, action.game)
        self.actions_stack.append(action)
        return self

    def run(self) -> ProcessingStatus:
        status = self._subrunner()
        if self.autosave:
            self._save_game_objects(status)
        return status

    def _round_counter(self):
        if self.game.stage == stages.SetupStage:
            # self.game.rounds_counter += 1
            logger.info(f'-- Game round #{self.game.rounds_counter} --')
            # self.game.presave()
            return self.NEW_ROUND
        return self.CONTINUE

    def _subrunner(self) -> ProcessingStatus:
        if self._round_counter() == self.FORCED_STOP:
            return self.FORCED_STOP

        headline = StrColors.bold('Processing')
        logger.info(f'{headline} {self.game}. ')

        # we are getting current stage from Game only once to cache their properties
        # when stage complited run(..) will be called again and we ask we new stage
        current_stage = self.game.stage

        # [01] actions
        if self._actions_processing(current_stage) == self.FORCED_STOP:
            return self.FORCED_STOP

        # [02] stages
        status = self._stage_processing(current_stage)
        if status in [self.STOP, self.FORCED_STOP]:
            return status

        # CONTINUE RECURSIVELY
        return self._subrunner()

    def _stage_complited(self, current_stage: BaseStage):
        self._make_history(current_stage)
        if self._premature_final_condition():  # go ahead:
            self._continue_to_next_stage()
        else:
            self._continue_to_final()

    def _premature_final_condition(self):
        # 1- all other players passed -> go to final
        conditions = [
            len(list(self.game.players.active)) > 1,
        ]
        return any(conditions)

    def _continue_to_next_stage(self):
        if self.game.stage_index + 1 < len(self.game.stages):
            self.game.stage_index += 1
        else:
            self.game.stage_index = 0
        self.game.presave()

    def _continue_to_final(self):
        opposing_index = self.game.stages.index(stages.OpposingStage)
        if self.game.stage_index == opposing_index:
            # game already complited final stage, so go to next
            self._continue_to_next_stage()
        else:
            self.game.stage_index = opposing_index
            self.game.presave()


class AutoProcessor(BaseProcessor):
    def __init__(
        self,
        game: Game,
        *,
        with_actions: list[ActionPrototype] = [],  # also could be stop factor
        stop_before_stage: Type[BaseStage] = None,
        stop_after_stage: Type[
            BaseStage
        ] = None,  # means: process this stage inclusevly
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
        logger.info(StrColors.purple(_) + f'Stop factor: {self.stop_factor}')

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
        # TRY `WITH ACTIONS`
        for proto in self.with_actions.copy():  # copy: because of removing items
            if proto.suitable_stage_class:
                if proto.suitable_stage_class != type(current_stage):
                    continue

            try:
                value = proto.action_values[0] if proto.action_values else None
                action = proto.get_action(value)

                if self.actions_stack:
                    raise NotImplementedError

                self.add(action)
                super()._actions_processing(current_stage)
                self.with_actions.remove(action)

                if self._stop_after_action_condition(proto) == self.FORCED_STOP:
                    return self.FORCED_STOP

            except ActionError:
                pass  # okey, try later
            finally:
                self.actions_stack.clear()

        # APPEND NEW AUTO GENERATED ACTION
        protos = current_stage.get_possible_actions()
        if not protos:
            return self.CONTINUE

        # take first action prototype with first (min) value
        proto = protos[0]
        value = proto.action_values[0] if proto.action_values else None
        action = proto.get_action(value)
        self.add(action)

        # CHECK STOP FACTOR AND ACTION PROCESSING
        if self.stop_factor.get('stop_before_action') == proto:
            return self.FORCED_STOP

        super()._actions_processing(current_stage)

        if self._stop_after_action_condition(proto) == self.FORCED_STOP:
            return self.FORCED_STOP

        if not current_stage.check_requirements(raises=False):
            # force making auto actions untill stage requirement will be satisfied
            return self._actions_processing(current_stage)

        return self.CONTINUE

    def _stage_processing(self, current_stage: BaseStage):
        if self.stop_factor.get('stop_before_stage') == current_stage:
            return self.FORCED_STOP

        status = super()._stage_processing(current_stage)

        if self.stop_factor.get('stop_after_stage') == current_stage:
            return self.FORCED_STOP

        # second check for stop_before_stage: when stage has been complited (CONTINUE)
        # stage_index goes to next stage and we need to re-check if this stage is stop
        # factor. if yes, we need to interrupt processing to prevent auto acting actions
        # at this new stage.
        if status == self.CONTINUE:
            if self.stop_factor.get('stop_before_stage') == self.game.stage:
                return self.FORCED_STOP

        return status
