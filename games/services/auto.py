from __future__ import annotations

import pytest
from core.functools.utils import StrColors, init_logger, logging
from games.models import Game, Player
from games.services import actions
from games.services.actions import ActError, ActionContainer, ActionPreform
from games.services.stages import StagesContainer
from users.models import User
from typing import cast

logger = init_logger(__name__, logging.DEBUG)

ROUND_MESSAGE = '\n\t#############\n\t' 'GAME ROUND #{count} ' '\n\t#############'


def autoplay_game(
    game: Game,
    *,
    with_actions: list[ActionPreform] = [],
    stop_before_stage: str = '',
    stop_after_stage: str = '',  # means: process this stage inclusevly
    stop_before_action_at_stage: ActionPreform = None,
    stop_after_action_at_stage: ActionPreform = None,
):
    params = [
        stop_before_stage,
        stop_after_stage,
        stop_before_action_at_stage,
        stop_after_action_at_stage,
    ]
    params = list(filter(bool, params))
    assert params, 'No stop condition provided. '
    assert len(params) == 1, 'Many condition provided, expect only one. '
    param = params[0]

    if param in [stop_after_action_at_stage, stop_before_action_at_stage]:
        assert isinstance(param, ActionPreform), 'Action shoud be ActionPreform. '

    for a in with_actions:
        assert a != param, '`with actions` cannot contain stop factor'


    key_stage = None
    if stop_after_stage:
        key_stage = StagesContainer.get_next(stop_after_stage).__name__
    if stop_before_stage:
        key_stage = stop_before_stage
    if key_stage:
        assert StagesContainer.get(key_stage), 'invalid stage name provided'

    logger.info(
        StrColors.purple(f'[0] autoplay game (stop factor: {param})')
    )

    game_rounds_counter = 0
    while True:
        if game.stage.name == 'SetupStage':
            game_rounds_counter += 1
            logger.info(ROUND_MESSAGE.format(count=game_rounds_counter))
        if game_rounds_counter > game.players.count():
            raise RuntimeError(
                'To many game round iterations. It makes no sense. Probably autoplaying will '
                'never reach stop condition: '
                f'{stop_before_action_at_stage or stop_after_action_at_stage}. '
                f'Check attributes provided to autoplay_game(..). '
            )

        for a in with_actions.copy():
            try:
                a.act(game, continue_processing_after=False)
                with_actions.remove(a)
            except ActError:
                # okey, try later
                pass

        if game.stage.necessary_action and game.stage.performer:
            action_class = ActionContainer.get(game.stage.necessary_action)
            value = game.stage.get_necessary_action_values().get('min')
            current_action = action_class(
                game, game.stage.performer.user, value=value, act_immediately=False
            )

            if stop_before_action_at_stage == current_action:
                # have to call for save() here,
                # because action act(..) does not call for save(..) at the end
                b = stop_before_action_at_stage == current_action
                game.save()
                break

            current_action.act(continue_processing_after=False)

            if stop_after_action_at_stage  == current_action:
                game.save()
                break

        response = StagesContainer.continue_processing(game, stop_stage=key_stage or '')
        if response['status'] == 'success':
            # no savings here
            # game was saved at continue_processing when reached stop factor
            break
        elif response['status'] == 'forced_stop':
            continue
        else:
            raise RuntimeError('unexpected response status recived')

    if with_actions:
        raise RuntimeError('Reach stop factor, but no all `with_actions` was acted. ')
