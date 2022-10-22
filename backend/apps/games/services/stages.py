from __future__ import annotations
from copy import copy

from pprint import pformat
from typing import TYPE_CHECKING, Any, Callable, Iterable, Type, TypeAlias

from black import Sequence

from core.utils import Interval, StrColors, init_logger
from games.services import actions
from games.services.actions import ActionPrototype, BaseAction
from games.services.cards import CardList

if TYPE_CHECKING:
    from ..models import Player
    from ..models.game import Game
    _ActionValuesTypes: TypeAlias = int | Interval[int] | Sequence[Player] | Player

logger = init_logger(__name__)


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
            f'Requirement <{name}> are not satisfied ({verbose_message}). \n'
            f'Possible actions: {possibles}. '
        )


class BaseStage:
    requirements: tuple[Callable[[BaseStage], bool], ...] = ()
    """Requirements for stage execution. """

    possible_actions_classes: tuple[Type[BaseAction], ...] = ()
    """Any possible actions at that stage (main action at 0 index). """

    message: str = 'stage has been proceed'
    """Message form for game `actions_history`. Formated at get_message_format. """
    message_requirement_unsatisfied: str = 'waiting for {player}'
    """Message form for stage `status`. Formated at get_status_format. """

    def get_message_format(self):
        return self.message

    def get_status_format(self):
        status = self.message_requirement_unsatisfied
        return status.format(player=self.performer)

    def __init__(self, game: Game) -> None:
        self.game = game

    def __repr__(self) -> str:
        return self.__class__.__name__

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type):
            # make a shortcut for that cases: if game.stage == BiddingStage: ...
            # check for strick types equality, not isinstance(..)
            # because BiddingStage_1 not equals to BiddingStage_2 and etc.
            return type(self) == other
        return super().__eq__(other)

    def get_possible_actions(
        self,
        from_origin_actions: Iterable[Type[actions.BaseAction]] | None = None,
    ) -> list[ActionPrototype[Any]]:
        """
        Return a set of all various prototypes for actions that could be acted. Note:
        Actions could be mutually exclusive and could not be able acted all together.
        """
        if from_origin_actions is None:
            from_origin_actions = self.possible_actions_classes

        if not self.performer:
            logger.warning('Asking for possible actions when there are no performer. ')
            return []

        possibles: list[ActionPrototype[Any]] = []
        for action_class in from_origin_actions:
            action_values = self.get_possible_values_for(action_class)
            possibles.append(
                action_class.prototype(self.game, self.performer, action_values)
            )

        # Append base actions wich are allowew at every stage for every player.
        # [1] LeaveGame
        for player in self.game.players.not_host:
            possibles.append(actions.LeaveGame.prototype(self.game, player))

        return possibles

    def is_values_awailable(self, action: Type[BaseAction] | BaseAction) -> bool:
        """
        Called inside get_possible_values_for(..) before preparing any values.
        """
        action_type = action if isinstance(action, type) else type(action)
        action_instance = action if isinstance(action, BaseAction) else None

        if action_type not in self.possible_actions_classes:
            logger.error('Asking for necessary values for not supported action. ')
            return False

        if self.performer is None:
            logger.error('Asking for necessary values when there are no performer. ')
            return False

        if not action_type.values_expected:
            if not action_instance:
                # [NOTE]
                # for action type None is returned.
                # for action instances otherwise values will be prepared in sub classes.
                # (for action instaces we always preparing a values because they ask
                # them at self init methods)
                return False

        return True

    def get_possible_values_for(
        self, action: Type[BaseAction] | BaseAction
    ) -> _ActionValuesTypes | None:
        if not self.is_values_awailable(action):
            return None
        raise NotImplementedError('Must be implemented in subclass. ')

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
    possible_actions_classes = (
        actions.StartAction,
        actions.KickOut,
    )
    message: str = 'game begins'
    message_requirement_unsatisfied: str = 'wait while {player} start this game'

    def enough_players_requirement(self):
        return len(self.game.players) > 1

    def enough_money_requirement(self):
        smallest_bank = self.game.players.aggregate_min_users_bank()
        return self.game.config.big_blind <= smallest_bank

    def host_approved_start_requirement(self):
        return self.game.begins

    requirements = (
        enough_players_requirement,
        enough_money_requirement,
        host_approved_start_requirement,
    )

    def get_possible_actions(
        self, from_origin_actions: Iterable[Type[actions.BaseAction]] | None = None
    ) -> list[ActionPrototype]:
        if not all(
            (self.enough_players_requirement(), self.enough_money_requirement())
        ):
            # pre-check requrimants fails, StartAction unawailable
            from_origin_actions = []

        return super().get_possible_actions(from_origin_actions)

    def get_possible_values_for(
        self, action: Type[BaseAction] | BaseAction
    ) -> _ActionValuesTypes | None:
        if not self.is_values_awailable(action):
            return None
        return self.game.players.not_host

    def get_performer(self) -> Player:
        return self.game.players.host

    def execute(self):
        self.fill_and_shuffle_deck()

    def fill_and_shuffle_deck(self):
        generator = self.game.config.deck.generator

        if callable(generator):
            self.game.deck = CardList(instance=generator(self.game.config.deck))
        elif isinstance(generator, CardList):
            self.game.deck = generator.copy()
        else:
            raise TypeError

        if self.game.config.deck.shuffling:
            self.game.deck.shuffle()


class DealCardsStage(BaseStage):
    """Pre-flop: draw cards to all players."""

    amount: int
    message: str = 'deal {amount} cards to players'

    def __init__(self, game: Game) -> None:
        super().__init__(game)

        try:
            index = int(self.__class__.__name__[-1]) - 1
        except ValueError as e:
            # [FIXME] here is a tmp solution. we need to get rid of the stage indexes
            #
            if len(self.game.config.deal_cards_amounts) == 1:
                index = 0
            else:
                raise ValueError(
                    'Stage class with `amount` property must ends with index.'
                )

        self.amount = self.game.config.deal_cards_amounts[index]

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

    def all_players_haggled_requirement(self):
        return not bool(list(self.game.players.without_bet))

    def all_beds_equal_requirement(self):
        return self.game.players.check_bet_equality()

    requirements = (
        all_players_haggled_requirement,
        all_beds_equal_requirement
    )

    message: str = 'bets are accepted'
    message_requirement_unsatisfied: str = 'wait while {player} place his bet'

    def get_performer(self) -> Player:
        return self.game.players.next_betmaker

    def get_possible_actions(
        self,
        from_origin_actions: Iterable[Type[actions.BaseAction]] | None = None,
    ) -> list[ActionPrototype]:
        if from_origin_actions is None:
            from_origin_actions = self.possible_actions_classes
        origin = list(from_origin_actions)

        # we take origin[0] because it contains basic (main) action
        values = self.get_possible_values_for(origin[0])
        if not values:
            return super().get_possible_actions(origin)

        # cut out exccess actions:
        if values.min == 0:
            origin.remove(actions.PlaceBetReply)  # nothing to reply
            origin.remove(actions.PassAction)  # there are not bet chalenging
        else:
            origin.remove(actions.PlaceBetCheck)  # chalenging bet on the table

        if values.min == values.max:
            origin.remove(actions.PlaceBet)  # other actions provided
            origin.remove(actions.PlaceBetVaBank)  # other actions provided

        return super().get_possible_actions(origin)

    def get_possible_values_for(
        self, action: Type[BaseAction] | BaseAction
    ) -> Interval[int] | None:
        if not self.is_values_awailable(action):
            return None

        # that checked at 'is_values_awailable', but assertion here to avoid mypy error
        assert self.performer

        step = self.game.config.bet_multiplicity
        min = self.game.players.aggregate_max_bet() - self.performer.bet_total
        max = self.game.players.aggregate_possible_max_bet_for_player(self.performer)
        max = max - (max % step)
        return Interval(min=min, max=max, step=step)

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
        try:
            first, second = (next(iterator), next(iterator))
        except StopIteration:
            # only one player in game
            return True
        return (
            first.bet_total == self.game.config.small_blind
            and second.bet_total == self.game.config.big_blind
        )

    requirements = (players_have_placed_blinds,)  # type: ignore

    def get_performer(self) -> Player:
        """Next 2 player after dealer."""
        iterator = self.game.players.after_dealer_all
        first, second = (next(iterator), next(iterator))
        if first.is_active and first.bet_total != self.game.config.small_blind:
            return first
        if second.is_active and second.bet_total != self.game.config.big_blind:
            return second

        raise RuntimeError

    def get_possible_values_for(self, action: Type[BaseAction] | BaseAction):
        if not self.is_values_awailable(action):
            return None

        if self.performer == next(self.game.players.after_dealer_all):
            return self.game.config.small_blind
        return self.game.config.big_blind

    def execute(self):
        # we need to ovveride super().execute() because it will call accept_bets, but we
        # do not need it at PlacingBlinds stage
        pass  # do nothing


class FlopStage(BaseStage):
    """Place cards on the table."""

    message: str = 'flop {amount} cards on game table'
    amount: int

    def __init__(self, game: Game) -> None:
        super().__init__(game)

        try:
            index = int(self.__class__.__name__[-1]) - 1
        except ValueError as e:
            raise ValueError('Stage class with `amount` property must ends with index.')
        self.amount = self.game.config.flops_amounts[index]

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
        winners = list(self.game.players.winners)
        reminder = self.game.bank % len(winners)
        if reminder > 0:
            raise NotImplementedError

        benefit = self.game.bank // len(winners)

        for player in winners:
            self.game.bank -= benefit
            player.user.profile.bank += benefit
            player.user.profile.presave()
        self.game.presave()

        logger.info(
            'Combinations by players: \n'
            + pformat([(player, player.combo) for player in self.game.players])
        )
        self.message_format_kwargs = {
            'winners': ' '.join([p.user.username for p in winners]),
            'combo': winners[0].combo.kind.name,
            'benefit': benefit,
        }


class TearDownStage(BaseStage):
    possible_actions_classes = (actions.EndAction,)
    message: str = 'game round is over'
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
        self.game.actions_history.clear()
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


########################################################################################
#       Default Stages
########################################################################################

# [TODO] get rid of stage sufixes, use splecial class counter
#
DealCardsStage_1 = DealCardsStage.factory('DealCardsStage_1')
DealCardsStage_2 = DealCardsStage.factory('DealCardsStage_2')
DealCardsStage_3 = DealCardsStage.factory('DealCardsStage_3')

BiddingsStage_1 = BiddingsStage.factory('BiddingsStage_1')
BiddingsStage_2 = BiddingsStage.factory('BiddingsStage_2')
BiddingsStage_3 = BiddingsStage.factory('BiddingsStage_3')
BiddingsStage_4 = BiddingsStage.factory('BiddingsStage_4')

FlopStage_1 = FlopStage.factory('FlopStage_1')
FlopStage_2 = FlopStage.factory('FlopStage_2')
FlopStage_3 = FlopStage.factory('FlopStage_3')
