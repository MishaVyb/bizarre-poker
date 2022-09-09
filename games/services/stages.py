from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING, Callable

from core.functools.utils import StrColors, init_logger
from django.db import models
from games.backends.cards import CardList, Decks
from games.services.configurations import DEFAULT
from core.functools.looptools import circle_after

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
        return (
            f'{StrColors.bold("Stop processing")}. '
            f'Requirement {self.requirement_name} are not satisfied. '
            f'Waiting for {self.stage.performer} act {self.stage.necessary_action}'
        )


class BaseGameStage:
    requirements: list[Callable] = []

    # We can not import actions module here because it using StagesContainer defined
    # here. Еherefore using str name to splecify a necessart action.
    necessary_action: str | None = None

    def __init__(self, game: Game) -> None:
        self.game = game

    @property
    def performer(self) -> None | Player:
        return None

    def __str__(self) -> str:
        return self.__class__.__name__

    def get_necessary_action_values(self) -> dict:
        return {}

    def check_requirements(self, *, raises=True):
        for r in self.requirements:
            if not r(self):
                if raises:
                    raise StageProcessingError(self, r.__name__)
                return False
        return True

    def process(self) -> None:
        self.check_requirements()

    @classmethod
    def factory(cls, name: str | None = None, **kwargs) -> type[BaseGameStage]:
        return type(name or cls.__name__, (cls,), kwargs)


class SetupStage(BaseGameStage):
    necessary_action = 'StartAction'

    def host_approved_game_start(self):
        return self.game.begins

    requirements = [host_approved_game_start]

    @property
    def performer(self):
        if self.check_requirements(raises=False):
            return None
        return self.game.players.host if self.game.players else None

    def process(self):
        super().process()
        self.fill_and_shuffle_deck()

    def fill_and_shuffle_deck(self):
        deck = getattr(Decks, self.game.deck_generator)

        if callable(deck):
            self.game.deck = CardList(instance=deck())
        elif isinstance(deck, CardList):
            self.game.deck = CardList(instance=deck)
        else:
            raise TypeError

        if DEFAULT.deck_shuffling:
            self.game.deck.shuffle()


class DealCardsStage(BaseGameStage):
    """Pre-flop: draw cards to all players."""

    amount: int

    def process(self):
        for _ in range(self.amount):
            for player in self.game.players:
                player.hand.append(self.game.deck.pop())
                player.save()


class BiddingsStage(BaseGameStage):
    necessary_action = 'PlaceBet'

    @property
    def performer(self):
        """Next player after last bet maker. Starting from first after dealer"""
        if self.check_requirements(raises=False):
            return None
        return self.game.players.order_by_bet.first()

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

    def process(self) -> None:
        super().process()
        self.accept_bets()

    def accept_bets(self) -> None:
        logger.info(f'Accepting beds: {[str(p.bets) for p in self.game.players]}')

        income = 0
        for p in self.game.players:
            for b in p.bets.all():
                income += b.value
                b.delete()

        self.game.bank += income


class PlacingBlindsStage(BiddingsStage):
    necessary_action = 'PlaceBlind'

    def players_have_placed_blinds(self):
        return bool(
            self.game.players.after_dealer[0].bets.total == DEFAULT.small_blind
            and self.game.players.after_dealer[1].bets.total == DEFAULT.big_blind
        )

    requirements = [players_have_placed_blinds]  # type: ignore

    def get_necessary_action_values(self) -> dict:
        if self.performer == self.game.players.after_dealer.first():
            return {
                'min': DEFAULT.small_blind,
                'max': DEFAULT.small_blind,
            }
        return {
            'min': DEFAULT.big_blind,
            'max': DEFAULT.big_blind,
        }

    def process(self) -> None:
        # do not calling for super().process() becouse it will call accept_bets, but we
        # do not need it at PlacingBlinds stage
        self.check_requirements()


class FlopStage(BaseGameStage):
    """Place cards on the table."""

    amount: int

    def process(self) -> None:
        flop = self.game.deck[-self.amount :]
        self.game.table.extend(reversed(flop))
        del self.game.deck[-self.amount :]


class OpposingStage(BaseGameStage):
    def process(self) -> None:

        players = list(self.game.players.active)
        # for player in players:

        # taking first group
        priority, winners_iter = next(
            itertools.groupby(players, key=lambda p: p.combo.kind.priority)
        )
        winners = list(winners_iter)
        reminder = self.game.bank % len(winners)
        if reminder > 0:
            raise NotImplementedError

        share = self.game.bank // len(winners)

        for player in winners:
            self.game.bank -= share
            player.user.profile.deposit_in(share)

        logger.info(StrColors.underline('Game summary'))
        logger.info(f'Combos: {[p.combo for p in self.game.players.active]}')
        logger.info(f'Winners: {winners}')


class TearDownStage(BaseGameStage):
    def process(self) -> None:
        self.game.begins = False
        self.game.deck.clear()
        self.game.table.clear()
        for player in self.game.players:
            player.hand.clear()
            player.is_active = True
            player.save()


class MoveDealerButton(BaseGameStage):
    def process(self) -> None:
        pass


########################################################################################


class StagesContainer:
    stages: tuple[type[BaseGameStage], ...] = (
        SetupStage,
        DealCardsStage.factory(amount=2),
        PlacingBlindsStage,
        BiddingsStage.factory('BiddingsStage-1'),
        FlopStage.factory('FlopStage-1', amount=3),
        BiddingsStage.factory('BiddingsStage-2'),
        FlopStage.factory('FlopStage-2', amount=1),
        BiddingsStage.factory('BiddingsStage-3'),
        FlopStage.factory('FlopStage-3', amount=1),
        BiddingsStage.factory('BiddingsStage-4(final)'),
        OpposingStage,
        # stages for preparing next game
        TearDownStage,
        MoveDealerButton,
    )

    @classmethod
    def get(cls, name: str):
        try:
            return next(filter(lambda x: x.__name__ == name, cls.stages))
        except StopIteration:
            raise ValueError(
                f'Invalid action name: {name}. '
                f'Available actions: {[a.__name__ for a in cls.stages]}'
            )

    @classmethod
    def get_next(cls, name: str):
        try:
            return next(
                circle_after(lambda x: x.__name__ == name, cls.stages, inclusive=False)
            )
        except StopIteration:
            raise ValueError(
                f'Invalid action name: {name}. '
                f'Available actions: {[a.__name__ for a in cls.stages]}'
            )

    @classmethod
    def continue_processing(
        cls, game: Game, *, stop_stage: str = ''
    ) -> StageProcessingError | None:
        # logging:
        headline = StrColors.bold('Processing')
        detail = (
            (
                f'Stage performer: {game.stage.performer}. '
                f'Necessary action: {game.stage.necessary_action}. '
            )
            if game.stage.performer
            else ''
        )
        logger.info(f'{headline} {game}. {detail}')

        # process curent stage:
        try:
            game.stage.process()
        except StageProcessingError as e:
            logger.info(e)
            game.save()
            return e

        # successfully! go to the next stage:
        if game.stage_index + 1 < len(cls.stages):
            game.stage_index += 1
        else:
            game.stage_index = 0

        # check exit condition:
        if stop_stage == str(game.stage):
            game.save()
            return None

        # CONTINUE RECURSIVELY
        # Do not calling for save() once again.
        # Only when StageProcessingError will be catched and processor will stop.
        return cls.continue_processing(game)
