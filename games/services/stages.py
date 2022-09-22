from __future__ import annotations

import itertools
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Callable

from core.functools.looptools import circle_after
from core.functools.utils import StrColors, init_logger
from games.services.cards import CardList, Decks
from games.services.configurations import DEFAULT

if TYPE_CHECKING:
    from ..models import Player
    from ..models.game import Game

logger = init_logger(__name__)


class StageProcessingError(Exception):
    def __init__(self, stage: BaseGameStage, requirement_name: str) -> None:
        self.stage = stage
        self.requirement_name = requirement_name
        super().__init__()

    def __str__(self) -> str:
        return (
            f'{StrColors.bold("Stop processing")}. '
            f'Requirement {self.requirement_name} are not satisfied. Waiting...'
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

    @property
    def performer_report(self):
        if not self.performer:
            return ''

        value = self.get_necessary_action_values()
        value_detail = f'with {value}' if value else ''
        return (
            f'Stage performer: {self.performer}. '
            f'Necessary action: {self.necessary_action} {value_detail}'
        )

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.name

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
                player.presave()


class BiddingsStage(BaseGameStage):
    necessary_action = 'PlaceBet'

    @property
    def performer(self):
        """Next player after last bet maker. Starting from first after dealer"""
        if self.check_requirements(raises=False):
            return None
        return next(self.game.players.order_by_bet)

    def get_necessary_action_values(self) -> dict:
        if self.performer is None:
            raise NotImplementedError

        max_bet = self.game.players.aggregate_max_bet()
        performer_bet = self.performer.bet_total
        min_value = max_bet - performer_bet

        max_value = self.game.players.aggregate_min_users_bank()
        return {'min': min_value, 'max': max_value}

    def every_player_place_bet_or_say_pass(self):
        return not bool(list(self.game.players.without_bet))

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
        logger.info(f'Accepting beds: {[p.bet_total for p in self.game.players]}')

        income = self.game.players.aggregate_sum_all_bets()
        self.game.players_manager.all_bets().delete()
        self.game.players_manager.update_annotation(bet_total=0)
        self.game.bank += income


class PlacingBlindsStage(BiddingsStage):
    necessary_action = 'PlaceBlind'

    def players_have_placed_blinds_or_passed(self):
        iterator = self.game.players.after_dealer_all
        first, second = (next(iterator), next(iterator))
        return bool(
            (not first.is_active or first.bet_total == DEFAULT.small_blind)
            and (not second.is_active or second.bet_total == DEFAULT.big_blind)
        )

    requirements = [players_have_placed_blinds_or_passed]  # type: ignore

    @property
    def performer(self):
        """Next 2 player after dealer."""
        if self.check_requirements(raises=False):
            return None

        iterator = self.game.players.after_dealer_all
        first, second = (next(iterator), next(iterator))
        if first.is_active and first.bet_total != DEFAULT.small_blind:
            return first
        if second.is_active and second.bet_total != DEFAULT.big_blind:
            return second

        raise RuntimeError

    def get_necessary_action_values(self) -> dict:
        if self.performer == next(self.game.players.after_dealer_all):
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
        flop = self.game.deck[-self.amount:]
        self.game.table.extend(reversed(flop))
        del self.game.deck[-self.amount:]
        self.game.presave()


class OpposingStage(BaseGameStage):
    def process(self) -> None:
        combo, winners_iter = next(
            itertools.groupby(self.game.players.active, attrgetter('combo'))
        )
        winners = list(winners_iter)
        reminder = self.game.bank % len(winners)
        if reminder > 0:
            raise NotImplementedError

        share = self.game.bank // len(winners)

        for player in winners:
            self.game.bank -= share
            player.user.profile.bank += share
            player.user.profile.presave()
        self.game.presave()

        logger.info(
            f'{StrColors.underline("Game summary")}'
            f'Combos: {[p.combo for p in self.game.players.active]}'
            f'Winners: {winners}'
        )


class TearDownStage(BaseGameStage):
    def process(self) -> None:
        self.game.begins = False
        self.game.deck.clear()
        self.game.table.clear()
        for player in self.game.players:
            player.hand.clear()
            player.is_active = True
            player.pre_save()


class MoveDealerButton(BaseGameStage):
    def process(self) -> None:
        n = len(self.game.players)
        self.game.players[0].is_dealer = False
        self.game.players[0].position = n - 1  # become last
        self.game.players[0].pre_save()

        self.game.players[1].is_dealer = True
        self.game.players[1].position = 0
        self.game.players[1].pre_save()

        for player, position in zip(self.game.players[2:], range(1, n)):
            player.position = position
            player.pre_save()

        # re-order PlayerSelector
        self.game.players.reorder_source()


########################################################################################
# Stages Container - Main Game Processing
########################################################################################

def save_game_objects(game: Game):
    """Saving game, players, and users banks. Only if presave flag is True."""
    game.save(only_if_presave=True)
    for player in game.players:
        player.save(only_if_presave=True)
        player.user.profile.save(only_if_presave=True)


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

        # stages for preparing next game:
        TearDownStage,
        MoveDealerButton,
    )

    _save_after_proces_stoped: bool = True

    @classmethod
    def get(cls, name: str):
        if not name:
            raise ValueError('No name')
        try:
            return next(filter(lambda x: x.__name__ == name, cls.stages))
        except StopIteration:
            raise ValueError(
                f'Invalid stage name: {name}. '
                f'Available stages: {[a.__name__ for a in cls.stages]}'
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
    def continue_processing(cls, game: Game, *, stop_stage: str = '') -> dict[str, Any]:
        # logging:
        headline = StrColors.bold('Processing')
        logger.info(f'{headline} {game}. {game.stage.performer_report}')

        try:
            game.stage.process()  # process curent stage:
        except StageProcessingError as e:
            logger.info(f'{e}. ')
            if cls._save_after_proces_stoped:  # SAVING
                save_game_objects(game)
            return {'status': 'forced_stop', 'error': e}

        # successfully! go to the next stage:
        if game.stage_index + 1 < len(cls.stages):
            game.stage_index += 1
        else:
            game.stage_index = 0
        game.presave()

        # check exit condition:
        if stop_stage == game.stage.name:
            if cls._save_after_proces_stoped:  # SAVING
                save_game_objects(game)
            return {'status': 'success'}

        # CONTINUE RECURSIVELY
        # Do not calling for save() once again.
        # Only when StageProcessingError will be catched and processor will stop.
        return cls.continue_processing(game, stop_stage=stop_stage)
