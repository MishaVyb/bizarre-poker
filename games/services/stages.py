from __future__ import annotations


import itertools
from operator import attrgetter
from typing import TYPE_CHECKING, Callable, NamedTuple, Type, TypeAlias

from core.functools.utils import Interval, StrColors, init_logger
from games.services import actions
from games.services.actions import ActionPrototype, BaseAction
from games.services.cards import CardList, Decks
from games.services.configurations import DEFAULT


if TYPE_CHECKING:
    from ..models import Player
    from ..models.game import Game

logger = init_logger(__name__)

_AVP: TypeAlias = list[int] | Interval[int] | None
'Action values types at action prototype'


class RequirementNotSatisfied(Exception):
    def __init__(self, stage: BaseStage, requirement_name: str) -> None:
        self.stage = stage
        self.requirement_name = requirement_name

        super().__init__()

    def __str__(self) -> str:
        headline = StrColors.bold('Stop processing')
        name = self.requirement_name
        verbose_message = self.stage.message_requirement_unsatisfied.format(
            player=StrColors.underline(self.stage.performer)
        )
        possibles = "".join(map(str, self.stage.get_possible_actions()))
        return (
            f'{headline}. '
            f'Requirement <{name}> are not satisfied ({verbose_message}). '
            f'Possible actions: {possibles}. '
        )


class BaseStage:
    requirements: tuple[Callable[[BaseStage], bool], ...] = ()
    """Requirements for stage execution. """

    possible_actions_classes: tuple[type[BaseAction], ...] = ()
    """All possible. """

    message: str = ''
    message_requirement_unsatisfied: str = '{player}'

    def get_message_format(self):
        return self.message

    def __init__(self, game: Game) -> None:
        self.game = game

    def __repr__(self) -> str:
        return f'{self.__class__.__name__} at {self.game}'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type):
            # make a shortcut for that cases: if game.stage == BiddingStage: ...
            # check for strick types equality, not isinstance(..)
            return type(self) == other
        return super().__eq__(other)

    def get_possible_actions(self) -> list[ActionPrototype]:
        """
        Return a set of all various prototypes for actions that could be acted. Note:
        Actions could be mutually exclusive and could not be able acted all together.
        """
        if not self.performer:
            logger.warning('Asking for possible actions when there are no performer. ')
            return []

        possible = []
        for action_class in self.possible_actions_classes:
            action_values = self.get_possible_values_for(action_class)
            possible.append(
                action_class.prototype(self.game, self.performer, action_values)
            )

        # cut out exess actions
        ...
        # actions.PlaceBet,
        # actions.PlaceBetCheck,
        # actions.PlaceBetReply,
        # actions.PlaceBetVaBank,
        # actions.PassAction,

        return possible

    def get_possible_values_for(self, action: Type[BaseAction] | BaseAction) -> _AVP:
        action_type = action if isinstance(action, type) else type(action)
        action_instance = action if isinstance(action, BaseAction) else None

        if action_type not in self.possible_actions_classes:
            logger.error('Asking for necessary values for not supported action. ')
            return None

        if self.performer is None:
            logger.error('Asking for necessary values when there are no performer. ')
            return None

        if not action_type.values_expected:
            # only if not action_instance, otherwise [] returned
            # (for action instaces we alwayse preparing a values
            # because they aks them at self init methods)
            if not action_instance:
                return None

        return []

    @property
    def performer(self) -> None | Player:
        if self.check_requirements(raises=False):
            return None
        return self.get_performer()

    def get_performer(self) -> Player:
        raise NotImplementedError

    def check_requirements(self, *, raises=True):
        for requirement in self.requirements:
            if not requirement(self):
                if raises:
                    raise RequirementNotSatisfied(self, requirement.__name__)
                return False
        return True

    def execute(self) -> None:
        raise NotImplementedError

    @classmethod
    def factory(cls, name: str | None = None, **kwargs) -> type[BaseStage]:
        return type(name or cls.__name__, (cls,), kwargs)


class SetupStage(BaseStage):
    possible_actions_classes = (actions.StartAction,)
    message: str = 'game begins'
    message_requirement_unsatisfied: str = 'wait while {player} start this game'

    requirements = (
        lambda self: self.game.begins,
        lambda self: len(self.game.players) > 1,
    )

    def get_performer(self) -> Player:
        return self.game.players.host

    def execute(self):
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


class DealCardsStage(BaseStage):
    """Pre-flop: draw cards to all players."""

    amount: int = DEFAULT.deal_cards_amount
    message: str = 'deal {amount} cards to players'

    def get_message_format(self):
        return self.message.format(amount=self.amount)

    def execute(self) -> None:
        for _ in range(self.amount):
            for player in self.game.players:
                player.hand.append(self.game.deck.pop())
                player.presave()


class BiddingsStage(BaseStage):
    possible_actions_classes = (
        actions.PlaceBet,
        actions.PlaceBetCheck,
        actions.PlaceBetReply,
        actions.PlaceBetVaBank,
        actions.PassAction,
    )
    requirements = (
        # every_player_place_bet_or_say_pass
        lambda self: not bool(list(self.game.players.without_bet)),
        # all_beds_equal
        lambda self: self.game.players.check_bet_equality(),
    )

    message: str = 'bets are accepted'
    message_requirement_unsatisfied: str = 'wait while {player} place his bet'

    def get_performer(self) -> Player:
        return self.game.players.next_betmaker

    def get_possible_values_for(self, action: Type[BaseAction] | BaseAction) -> _AVP:
        if super().get_possible_values_for(action) is None:
            return None

        assert self.performer # for mypy

        # max bet -minus- player's bet
        min_value = self.game.players.aggregate_max_bet() - self.performer.bet_total
        max_value = self.game.players.aggregate_possible_max_bet()
        return Interval(min_value, max_value)

    def execute(self):
        self.accept_bets()

    def accept_bets(self) -> None:
        logger.info(f'Accepting bets: {[p.bet_total for p in self.game.players]}')

        income = self.game.players.aggregate_sum_all_bets()
        for player in self.game.players:
            player.bets.clear()
            player.presave()
        self.game.bank += income


class PlacingBlindsStage(BiddingsStage):
    possible_actions_classes = (  # type: ignore
        actions.PlaceBlind,
        # actions.PassAction,   # depricated
    )
    message: str = 'blinds are accepted'
    message_requirement_unsatisfied: str = 'wait while {player} place his blind'

    def players_have_placed_blinds(self):
        iterator = self.game.players.after_dealer_all
        first, second = (next(iterator), next(iterator))
        return (
            first.bet_total == DEFAULT.small_blind
            and second.bet_total == DEFAULT.big_blind
        )

    requirements = (players_have_placed_blinds,)  # type: ignore

    def get_performer(self) -> Player:
        """Next 2 player after dealer."""
        iterator = self.game.players.after_dealer_all
        first, second = (next(iterator), next(iterator))
        if first.is_active and first.bet_total != DEFAULT.small_blind:
            return first
        if second.is_active and second.bet_total != DEFAULT.big_blind:
            return second

        raise RuntimeError

    def get_possible_values_for(self, action: Type[BaseAction] | BaseAction) -> _AVP:
        if super(BiddingsStage, self).get_possible_values_for(action) is None:
            return None

        if self.performer == next(self.game.players.after_dealer_all):
            return [DEFAULT.small_blind]
        return [DEFAULT.big_blind]

    def execute(self):
        # we need to ovveride super().execute() because it will call accept_bets, but we
        # do not need it at PlacingBlinds stage
        pass  # do nothing


class FlopStage(BaseStage):
    """Place cards on the table."""

    message: str = 'flop {amount} cards on game table. '
    amount: int  # defined at factory

    def get_message_format(self):
        return self.message.format(amount=self.amount)

    def execute(self):
        flop = self.game.deck[-self.amount :]
        self.game.table.extend(reversed(flop))
        del self.game.deck[-self.amount :]
        self.game.presave()


class OpposingStage(BaseStage):
    message: str = '{winners} has {combo} and wins {benefit}'
    message_format_kwargs: dict = {}

    def get_message_format(self):
        return self.message.format(**self.message_format_kwargs)

    def execute(self):
        combo, winners_iter = next(
            itertools.groupby(self.game.players.active, attrgetter('combo'))
        )
        winners = list(winners_iter)
        reminder = self.game.bank % len(winners)
        if reminder > 0:
            raise NotImplementedError

        benefit = self.game.bank // len(winners)

        for player in winners:
            self.game.bank -= benefit
            player.user.profile.bank += benefit
            player.user.profile.presave()
        self.game.presave()

        self.message_format_kwargs['winners'] = ' '.join(
            [p.user.username for p in winners]
        )
        self.message_format_kwargs['combo'] = winners[0].combo.kind.name
        self.message_format_kwargs['benefit'] = round(benefit / 100, 2)


class TearDownStage(BaseStage):
    possible_actions_classes = (actions.EndAction,)
    message: str = ''
    message_requirement_unsatisfied: str = (
        'wait while {player} confirm ending this game'
    )

    requirements = (lambda self: not self.game.begins,)  # host_approved_tear_down,

    def get_performer(self) -> Player:
        return self.game.players.host

    def execute(self):
        self.clean_game_data()
        self.move_dealler_button()

    def clean_game_data(self):
        self.game.rounds_counter += 1
        self.game.begins = False
        self.game.deck.clear()
        self.game.table.clear()
        self.game.presave()

        for player in self.game.players:
            player.hand.clear()
            player.is_active = True
            player.presave()

    def move_dealler_button(self):
        reordered: list[Player] = self.game.players[1:] + [self.game.players[0]]
        for i, player in enumerate(reordered):
            player.position = i
        self.game.select_players(reordered)

        return
        n = len(self.game.players)
        self.game.players[0].is_dealer = False
        self.game.players[0].position = n - 1  # becomes last
        self.game.players[0].presave()

        self.game.players[1].is_dealer = True
        self.game.players[1].position = 0
        self.game.players[1].presave()

        for player, position in zip(self.game.players[2:], range(1, n)):
            player.position = position
            player.presave()

        # re-order PlayerSelector
        self.game.players.reorder_source()
        positions = [p.position for p in self.game.players]
        logger.info(f'Moving dealer button. New players postions: {positions}')


########################################################################################
#       Default Stages
########################################################################################

BiddingsStage_1 = BiddingsStage.factory('BiddingsStage_1')
BiddingsStage_2 = BiddingsStage.factory('BiddingsStage_2')
BiddingsStage_3 = BiddingsStage.factory('BiddingsStage_3')
BiddingsStage_4 = BiddingsStage.factory('BiddingsStage_4')

FlopStage_1 = FlopStage.factory('FlopStage_1', amount=DEFAULT.flops_amounts[0])
FlopStage_2 = FlopStage.factory('FlopStage_2', amount=DEFAULT.flops_amounts[1])
FlopStage_3 = FlopStage.factory('FlopStage_3', amount=DEFAULT.flops_amounts[2])


DEFAULT_STAGES = (
    SetupStage,
    DealCardsStage,
    PlacingBlindsStage,
    BiddingsStage_1,
    FlopStage_1,
    BiddingsStage_2,
    FlopStage_2,
    BiddingsStage_3,
    FlopStage_3,
    BiddingsStage_4,
    OpposingStage,
    TearDownStage,
)
