from __future__ import annotations

from core.functools.decorators import temporally
from core.functools.utils import StrColors, init_logger
from games.models import Game
from games.services.actions import ActError, ActionContainer, ActionPreform
from games.services.stages import StagesContainer, save_game_objects

logger = init_logger(__name__)

MESSAGES = {
    #'round': '\n\t#############\n\tGAME ROUND #{count}\n\t#############',
    'round': 'game round #{count}',
    'iteration_error': (
        'To many game round iterations. It makes no sense. Probably autoplaying will '
        'never reach stop factor: {param}. '
        'Check attributes provided to autoplay_game(..). '
    ),
    'action_error': (
        'Reach stop factor: {param}, but no all `with_actions` have been acted. '
    ),
}


@temporally(StagesContainer, _save_after_proces_stoped=False)
def autoplay_game(
    game: Game,
    *,
    with_actions: list[ActionPreform] = [],
    stop_before_stage: str = '',
    stop_after_stage: str = '',  # means: process this stage inclusevly
    stop_before_action_at_stage: ActionPreform = None,
    stop_after_action_at_stage: ActionPreform = None,
    stop_after_rounds_amount: int | None = None,
    stop_after_actions_amount: int | None = None,
    autosave: bool = True,
):
    args = locals()
    args.pop('game')
    args.pop('autosave')
    args.pop('with_actions')
    params = list(filter(lambda key_and_value: key_and_value[1], args.items()))
    assert params, 'No stop condition provided. '
    assert len(params) == 1, f'Many condition provided, expect only one: {params}'
    param_name, param = params[0]

    if param in [stop_after_action_at_stage, stop_before_action_at_stage]:
        assert isinstance(param, ActionPreform), 'Action shoud be ActionPreform. '
    assert param not in with_actions, '`with actions` cannot contain stop factor'

    key_stage = None
    if stop_after_stage:
        key_stage = StagesContainer.get_next(stop_after_stage).__name__
    if stop_before_stage:
        key_stage = stop_before_stage
    if key_stage:
        assert StagesContainer.get(key_stage), 'invalid stage name provided'

    logger.info(StrColors.purple(f'autoplay game ({param_name} : {param})'))

    actions_counter = 0
    game_rounds_counter = 0
    game_rounds_amount = stop_after_rounds_amount or len(game.players)
    while True:
        if game.stage.name == 'SetupStage':
            logger.info(MESSAGES['round'].format(count=game_rounds_counter))
            game_rounds_counter += 1

        for a in with_actions.copy():  # copy -- because of removing
            try:
                a.act(game, continue_processing_after=False)
                with_actions.remove(a)
            except ActError:
                pass  # okey, try later

        if game.stage.necessary_action and game.stage.performer:
            action_class = ActionContainer.get(game.stage.necessary_action)
            value = game.stage.get_necessary_action_values().get('min')
            current_action = action_class(
                game,
                game.stage.performer.user,
                value=value,
                act_immediately=False,
            )

            if stop_before_action_at_stage == current_action:
                break

            # ACTION ACT:
            current_action.act(continue_processing_after=False)
            actions_counter += 1
            # ################

            if stop_after_action_at_stage == current_action:
                break

        # GAME PROCESSING:
        response = StagesContainer.continue_processing(game, stop_stage=key_stage or '')
        # ################

        if response['status'] == 'success':
            break  # break condition for stop before\after stage:
        if stop_after_actions_amount and stop_after_actions_amount >= actions_counter:
            break
        if game_rounds_counter >= game_rounds_amount:
            if not stop_after_rounds_amount:
                raise RuntimeError(MESSAGES['iteration_error'].format(param=param))
            break

    if with_actions:
        raise RuntimeError(MESSAGES['action_error'].format(param=param))

    # saving not at continue_porcessing(..), but here:
    if autosave:
        save_game_objects(game)
