"""
This mudule describes constraints to all games models.

We are not validating single objects at model layer, because constaings refer to all
other games related objects. Call validate_constraints(..) just before saving game
objects to check all dependences.
"""


from django.db import IntegrityError
from core.functools.utils import init_logger
from games.models.game import Game
from games.selectors import PlayerSelector

logger = init_logger(__name__)


def validate_constraints(game: Game):
    "Check constraints and clean values if could, otherwise raising IntegrityError."
    # [1] validate only this player instance
    ...

    # [2] validate players dependences
    # validate all player dependences at this Game with this player instance
    # replace game player list with self instence and operate with new list

    if not isinstance(game.players, PlayerSelector):
        logger.warning('Player selector is None. Player manager will be used insted. ')

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
