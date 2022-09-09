from __future__ import annotations

import pytest
from core.functools.utils import StrColors, init_logger, logging
from games.models import Game, Player
from games.services import actions
from games.services.actions import ActionContainer
from games.services.stages import StagesContainer
from users.models import User

logger = init_logger(__name__, logging.DEBUG)


@pytest.mark.usefixtures('setup_users')
class BaseGameProperties:
    usernames = ('vybornyy', 'simusik', 'barticheg')  # host username is 'vybornyy'
    game_pk: int

    @property
    def users(self) -> dict[str, User]:
        return {name: User.objects.get(username=name) for name in self.usernames}

    @property
    def users_list(self) -> list[User]:
        return [User.objects.get(username=name) for name in self.usernames]

    @property
    def game(self) -> Game:
        return Game.objects.get(pk=self.game_pk)

    @property
    def players(self) -> dict[str, Player]:
        return {p.user.username: p for p in self.game.players}

    @property
    def players_list(self) -> list[Player]:
        return [user.player_at(self.game) for user in self.users_list]

    def autoplay_game_untill(
        self,
        stage: str,
        stop_after_action: actions.BaseGameAction = None,
        *,
        inclusevly=False,
    ):
        detail = (
            f'Untill {stop_after_action.player} act {stop_after_action}. '
            if stop_after_action
            else ''
        )
        logger.info(
            StrColors.purple(
                f'[0] autoplay game untill {stage} ({inclusevly=}). {detail}'
            )
        )
        if inclusevly:
            assert not stop_after_action, 'not supported with inclusevly'
            stage = StagesContainer.get_next(stage).__name__

        while True:
            if self.game.stage.necessary_action:
                action_class = ActionContainer.get(self.game.stage.necessary_action)
                value = self.game.stage.get_necessary_action_values().get('min')
                if not self.game.stage.performer:
                    raise RuntimeError(
                        'if neccassery action is defined that slould be a performer'
                    )

                action = action_class(
                    self.game,
                    self.game.stage.performer.user,
                    value=value,
                    act_immediately=False,
                )
                action.check_conditions()
                logger.info(f'{action.player} {StrColors.green("acting")} {action}')
                action.act_subclass()

                if stage == str(self.game.stage) and stop_after_action == action:
                    break

                StagesContainer.continue_processing(action.game, stop_stage=stage)
            else:
                StagesContainer.continue_processing(self.game, stop_stage=stage)

            if not stop_after_action and stage == str(self.game.stage):
                break

    def __str__(self) -> str:
        return self.__class__.__name__
