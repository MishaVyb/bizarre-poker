from typing import Literal
from rest_framework import status
from rest_framework.exceptions import APIException

from games.models import Game
from games.services.actions import BaseAction


class ConflictState(APIException):
    status_code = status.HTTP_409_CONFLICT
    message = '{action} action for {player} not allowed for current game state'
    default_code = 'action_conflict'

    def __init__(
        self,
        action: BaseAction | str,
        game: Game | None = None,
        code = default_code,
    ):
        message = action
        if isinstance(action, BaseAction):
            message = self.message.format(action=action.name, player=action.player)
            game = action.game

        assert game, 'Game should be provided for complete error response'
        detail = {
            'detail': message,
            'code': code,
            'status': game.stage.get_status_format(),
        }
        super().__init__(detail)
