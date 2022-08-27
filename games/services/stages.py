from __future__ import annotations

from collections import OrderedDict
import itertools
import logging
from time import clock_settime
from typing import TYPE_CHECKING, Callable
from core.functools.utils import init_logger, StrColors
from core.functools.looptools import circle_after
from games.backends.cards import CardList, Decks

# from games.models.player import PlayerBet
from . import configurations
from django.db import models

if TYPE_CHECKING:
    from ..models import Player
    from ..models.game import Game

logger = init_logger(__name__, logging.INFO)


class StageProcessingError(Exception):
    def __init__(self, stage: BaseGameStage, requirement_name: str) -> None:
        self.stage = stage
        self.requirement_name = requirement_name
        super().__init__()

    def __str__(self) -> str:
        return f'Stop processing. Requirement {self.requirement_name} are not satisfied. Waiting for {self.stage.performer} act {self.stage.necessary_action}'


class BaseGameStage:
    requirements: list[Callable] = []
    """необходимые условия, чтобы действия считать выполненным.
    Фактически как валидация данных перед тем как их прниять (сохранить)"""
    necessary_action: str | None = None

    def __init__(self, game: Game) -> None:
        self.game = game

    @property
    def performer(self):
        return self.get_performer()

    def __str__(self) -> str:
        return self.__class__.__name__

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BaseGameStage):
            return NotImplemented
        return (
            # current stage could be a subclass of requested stage, but if not it's not
            isinstance(self, type(__o))
            and self.game == __o.game
            and self.performer == __o.performer
        )

    def get_necessary_action_values(self) -> dict:
        return {}

    def get_performer(self) -> Player | None:
        return None

    def check_requirements(self):
        for r in self.requirements:
            if not r(self):
                raise StageProcessingError(self, r.__name__)

        logger.info(f'All requirements for {self} satisfied. Processing...')

    def process(self) -> None:
        raise NotImplementedError

    @classmethod
    def factory(cls, name_suffix='', **kwargs) -> type[BaseGameStage]:
        return type(cls.__name__ + name_suffix, (cls,), kwargs)


class SetupStage(BaseGameStage):
    necessary_action = 'StartAction'

    def host_approved_game_start(self):
        return self.game.begins

    requirements = [host_approved_game_start]

    def get_performer(self) -> Player | None:
        return self.game.players.host

    def process(self):
        self.check_requirements()
        self.fill_and_shuffle_deck()

    def fill_and_shuffle_deck(self):
        deck = getattr(Decks, self.game.deck_generator)

        if callable(deck):
            self.game.deck = CardList(instance=deck())
        elif isinstance(deck, CardList):
            self.game.deck = CardList(instance=deck)
        else:
            raise TypeError

        if configurations.DEFAULT.deck_shuffling:
            self.game.deck.shuffle()


class DealCardsStage(BaseGameStage):
    """Pre-flop: draw cards to all players."""

    amount: int

    def process(self):
        if any(p.hand for p in self.game.players):
            logger.warning(
                f'Player has cards in hand at {self}. '
                'Clear all players hands for continue. '
            )
            for p in self.game.players:
                p.hand.clear()
                p.save()

        for _ in range(self.amount):
            for player in self.game.players:
                player.hand.append(self.game.deck.pop())
                player.save()


class PlacingBlindsStage(BaseGameStage):
    necessary_action = 'PlaceBlind'
    _small_blind = configurations.DEFAULT.small_blind
    _big_blind = configurations.DEFAULT.big_blind

    def players_have_placed_blinds(self):
        с = (
            self.game.players[1].bets.total == self._small_blind
            and self.game.players[2].bets.total == self._big_blind
        )
        return с

    requirements = [players_have_placed_blinds]

    def get_necessary_action_values(self) -> dict:
        if self.performer == self.game.players.after_dealer.first():
            return {'value': self._small_blind}
        return {'value': self._big_blind}

    def get_performer(self) -> Player | None:
        """Two next players after dealer."""
        if not self.game.players[1].bets.exists():
            return self.game.players[1]
        if not self.game.players[2].bets.exists():
            return self.game.players[2]
        return None

    def process(self) -> None:
        self.check_requirements()


class BiddingsStage(BaseGameStage):
    necessary_action = 'PlaceBet'

    def get_necessary_action_values(self) -> dict:
        if self.performer is None:
            raise NotImplementedError

        max_bet = self.game.players.aggregate_max_bet()
        performer_bet = self.performer.bet_total
        min_value = max_bet - performer_bet

        field = 'user__profile__bank'
        max_value = self.game.players.active.aggregate(min=models.Min(field))['min']

        return {'min': min_value, 'max': max_value}

    def every_player_place_bet_or_say_pass(self):
        return not self.game.players.without_bet.exists()

    def all_beds_equal(self):
        return self.game.players.check_bet_equality()

    requirements = [
        every_player_place_bet_or_say_pass,
        all_beds_equal,
    ]

    def get_performer(self) -> Player | None:
        """Next player after last bet maker. Starting from first after dealer"""
        return self.game.players.order_by_bet.first()

    def process(self) -> None:
        self.check_requirements()
        self.accept_bets()

    def accept_bets(self) -> None:
        logger.info(f'Accepting beds: {[str(p.bets) for p in self.game.players]}')

        income = 0
        for p in self.game.players:
            for b in p.bets.all():
                income += b.value
                b.delete()

        self.game.bank += income


# class BiddingsWithBlindsStage(BiddingsStage):

#     def blinds_are_placed(self):
#         pass

#     def __init__(self, game: Game, performer: Player | None = None) -> None:
#         super().__init__(game, performer)
#         self.requirements += [
#             self.__class__.blinds_are_placed    # type: ignore
#         ]


# class Flop(BaseGameAction):
#     """Place cards on the table."""

#     def __init__(self, name: str, flop_amount) -> None:
#         self.flop_amount = flop_amount
#         super().__init__(name)

#     def __call__(self):
#         for _ in range(self.flop_amount):
#             self.game.table.append(self.game.deck.pop())
class FlopStage(BaseGameStage):
    """Place cards on the table."""

    amount: int

    def process(self) -> None:
        for _ in range(self.amount):
            self.game.table.append(self.game.deck.pop())


class OpposingStage(BaseGameStage):
    pass


class TearDownStage(BaseGameStage):
    pass


class MoveDealerButton(BaseGameStage):
    pass


# class MoveDealerButton(BaseGameAction):
#     def __call__(self):
#         """and change all players posotion clockwise, because dealer is always at 0 positions"""

#         # move dealer
#         it = circle_after(lambda p: p.dealer, self.game.players)
#         try:
#             next(it).set_dealer(False)
#             next(it).set_dealer(True)
#         except ValueError as e:
#             logger.warning(f'Game has no dealer: {e} First player becomes it. ')
#             self.game.players.first().set_dealer(True)
#         except StopIteration as e:
#             logger.warning(f'Game has no players: {e}. ')

#         # re-range all players positions
#         for i, player in enumerate(circle_after(lambda p: p.dealer, self.game.players)):
#             player.position = i
#             player.save()

#     # def round_execution(self):
#     #     """Processing full game round iteration, all in one method.
#     #     Call round_setup if necceassery.
#     #     """
#     #     ...

#     # class GameIterator(models.Model):
#     # game: Game = models.OneToOneField(
#     #     Game, on_delete=models.CASCADE, related_name='_iteration'
#     # )

#     # text information
######################################################################################


######################################################################################


class StagesList(list[type[BaseGameStage]]):
    _default_stages: list[type[BaseGameStage]] = [
        SetupStage,
        DealCardsStage.factory(amount=2),
        PlacingBlindsStage,
        BiddingsStage.factory('-1'),
        FlopStage.factory('-1', amount=3),
        BiddingsStage.factory('-2'),
        FlopStage.factory('-2', amount=1),
        BiddingsStage.factory('-3'),
        FlopStage.factory('-3', amount=1),
        BiddingsStage.factory('-4(final)'),
        OpposingStage,
        TearDownStage,
        # actions for next game
        MoveDealerButton,
    ]

    def __init__(self, stages: list[type[BaseGameStage]] = _default_stages) -> None:
        super().__init__(stages)

    # def get_current_at(self, game: Game) -> BaseGameStage:
    #     return self[game.stage_index](game)

    def continue_processing(self, game: Game) -> StageProcessingError:  # type: ignore
        # обработаем текущий этап
        logger.info(
            StrColors.bold(f'Continue processing for {game}. ')
            + f'Stage performer: {game.stage.performer}. '
            + f'Necessary action: {game.stage.necessary_action} ...'
        )

        try:
            game.stage.process()
        except StageProcessingError as e:
            logger.info(StrColors.bold(str(e)))
            # game.stage_performer = e.stage.performer
            game.save()
            return e

        # если успешно прошли игровой этап (stage), то
        # проитерируем индекс на следующий шаг и обнулим перформера
        if game.stage_index + 1 < len(self):
            game.stage_index += 1
        else:
            game.stage_index = 0
        # game.stage_performer = None

        # рекурсивно продолжим процесс
        # save() не вызываем, так как игра будет сохранена при StageProcessingError
        self.continue_processing(game)


GAME_STAGES_LIST = StagesList()
