"""
This mudule describes constraints to all games models.

We are not validating single objects at model layer, because constaings refer to all
other games related objects. Call validate_constraints(..) just before saving game
objects to check all dependences.
"""
from __future__ import annotations


from typing import TYPE_CHECKING, Iterable
from django.db import IntegrityError
from core.functools.utils import StrColors, init_logger


from games.selectors import PlayerSelector

logger = init_logger(__name__)

if TYPE_CHECKING:
    from games.models.game import Game
    from games.models.player import Player


class GameContinuityError(RuntimeError):
    message = (
        'Do not use the same [{object}] but diferent instances. Player`s bet total '
        'will not work correctly and break down whole processing. {one} | {another}'
    )

    def __init__(
        self,
        one: Player | Game,
        another: Game | Player | Iterable[Player],
    ) -> None:

        super().__init__(
            self.message.format(object=one.__class__.__name__, one=one, another=another)
        )


def check_objects_continuity(
    one: Player | Game,
    another: Game | Player | Iterable[Player],
):
    another = another if isinstance(another, Iterable) else [another]
    if one not in another:
        raise RuntimeError(
            f'Check continuity failed. There are no equal objects: {one} | {another}'
        )

    if not any([one is other for other in another]):
        raise GameContinuityError(one, another)


def validate_constraints(game: Game):
    """Check constraints and clean values if could, otherwise raising IntegrityError."""
    # [1] validate game properties
    if not isinstance(game.get_players(), PlayerSelector):
        logger.warning('Player selector is None at validate_constraints(). ')

    # [2] validate game stage performer player
    if game.stage.performer is None:
        message = 'Game stage performer is None at cleaning before saving. '
        headline = StrColors.bold(StrColors.red(message))
        logger.warning(
            f'{headline}\n'
            f'{game} should to be saved only after processing raises an error '
            'and wait for some action from some performer. Exception: '
            'when running tests, we have to stop game at different stages. '
        )

    # [2] validate players dependences
    # validate all player dependences at this Game with this player instance
    # replace game player list with self instence and operate with new list

    # check host
    amount = len(list(filter(lambda p: p.is_host, game.players)))
    if not amount:
        raise IntegrityError(f'No hosts at {game}. ')
    if amount > 1:
        raise IntegrityError(f'Many hosts at {game}. ')

    # chek dealer
    # checking dealer has no sense, because it not an attribute, but jast a rule,
    # that player at 0 position is dealer (annotated via PlayerQuerySet)

    # ckeck players ordering by positions
    current = [p.position for p in game.players]
    expected = list(range(len(game.players)))
    if current != expected:
        current.sort()
        if current != expected:
            raise IntegrityError(f'{game} has invalid players positions: {current}. ')

        logger.warning(f'{game} has invalid players ordering: re-oredered here. ')
        game.players.reorder_source()
