import logging
from typing import Any, TypeVar

import pytest

from core.functools.utils import StrColors
from games.services import stages, actions, auto

from core.functools.utils import init_logger
from tests.base import BaseGameProperties, param_kwargs_list
from games.services.configurations import DEFAULT
from games.services.combos import Combo
from games.models import Player

logger = init_logger(__name__, logging.INFO)
_AT = TypeVar('_AT', bound=actions.BaseGameAction)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestGameStages(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    input_users_bank: dict[str, int]

    def test_flop_stage(self):
        # arrange
        auto.autoplay_game(self.game, stop_after_stage='SetupStage')
        input_deck = self.game.deck.copy()
        start = len(self.usernames) * DEFAULT.deal_cards_amount
        end = start + DEFAULT.flops_amounts[0]
        expected_flop = list(reversed(input_deck))[start:end]

        # act
        auto.autoplay_game(self.game, stop_after_stage='FlopStage-1')

        # assert
        assert self.game.table == expected_flop
        assert self.game.deck == input_deck[: len(input_deck) - end]

    def test_none_perfomer_after_stage_was_processed(self):
        auto.autoplay_game(self.game, stop_after_stage='BiddingsStage-1')
        assert self.game.stage.performer is None

    @pytest.mark.parametrize(
        'passed_names',
        [
            param_kwargs_list('01- no passed player', passed_names=set()),
            param_kwargs_list('02- 1 passed player', passed_names={'vybornyy'}),
        ],
    )
    def test_opposing_stage(
        self,
        setup_users_banks,
        setup_deck_get_expected_combos: tuple[list[Combo], list[list[int]]],
        passed_names: set[str],
    ):
        # Arrange.
        expected = setup_deck_get_expected_combos[0]
        rate_groups = setup_deck_get_expected_combos[1]
        passed_users = {self.users[name] for name in passed_names}
        active_users = set(self.users.values()) - passed_users

        # prepare winners and loosers set
        # (exclude passed players if they suppused to win)
        for rate_group in rate_groups:
            winners_indexes = rate_group
            winners = {self.users_list[i] for i in winners_indexes}
            winners = winners - passed_users    # filter out passed users
            if winners:
                break
            # if not (all potential winners have passed)
            # we will continue to the next rate group

        loosers = active_users - winners  # filter out winners

        # prepere expected loosing and winning values
        all_bets_together = len(active_users) * DEFAULT.big_blind
        benefit = all_bets_together // len(winners) - DEFAULT.big_blind
        loss = DEFAULT.big_blind

        # prepare pass actioins
        prepares: list[actions.ActionPreform] = []
        for user in passed_users:
            pass_ = actions.PassAction.preform(user)
            prepares.append(pass_)

        # Act. play game
        auto.autoplay_game(
            self.game, stop_after_stage='OpposingStage', with_actions=prepares
        )
        assert [p.combo for p in self.players_list] == expected

        # Assert winners banks
        for winner in winners:
            bank = self.input_users_bank[winner.username]
            assert winner.profile.bank == bank + benefit

        # Assert lissers banks
        for looser in loosers:
            bank = self.input_users_bank[looser.username]
            assert looser.profile.bank == bank - loss

        # Assert passed banks (it won`t change)
        for passed in passed_users:
            bank = self.input_users_bank[passed.username]
            assert passed.profile.bank == bank

    def test_move_dealer_button(self):
        # assertion before act:
        for player, expected_position in zip(self.players_list, [0, 1, 2, 3]):
            assert player.position == expected_position
        # act:
        auto.autoplay_game(self.game, stop_after_stage='MoveDealerButton')
        # assert:
        for player, expected_position in zip(self.players_list, [3, 0, 1, 2]):
            assert player.position == expected_position


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestGameActions(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    input_users_bank: dict[str, int]

    def test_start_action(self):
        # [1] test game stage before beginings
        logger.info(StrColors.purple('[1] test game stage before beginings'))

        # test begins flag
        assert self.game.begins is False

        # test who is performer, by default it should be host player
        # access through dinamic property "stage"
        assert self.game.stage.performer == self.players['vybornyy']
        # test nessacery action
        assert self.game.stage.necessary_action == 'StartAction'

        # [2] test game stages processing has not raised any exeption
        # game just has stoped processing and wait till player act neccessart action
        logger.info(StrColors.purple('[2] test game stages processing no failers'))
        stages.StagesContainer.continue_processing(self.game)

        # [3] test NOT host press "start"
        logger.info(StrColors.purple('[3] test NOT host press "start'))
        match = (
            r'Acting .* failed. '
            r'Game waiting for act from another player: .* vybornyy'
        )
        with pytest.raises(actions.ActError, match=match):
            actions.StartAction(self.game, self.users['simusik'])

        # [4]
        logger.info(StrColors.purple('[4] test host "start"'))
        actions.StartAction(self.game, self.users['vybornyy'])

    def test_place_blinds_action(self):
        actions.StartAction(self.game, self.users['vybornyy'])
        test = '[1] test there are no beds at beginings'
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[2] PlaceBlind by simusik | test beds values'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind(self.game, self.users['simusik'])
        assert [0, 5, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[3] PlaceBlind by vybornyy | test raises'
        logger.info(StrColors.purple(test))
        match = (
            r'Acting .* failed. '
            r'Game waiting for act from another player: .* barticheg'
        )
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBlind(self.game, self.users['vybornyy'])

        test = '[4] PlaceBlind by barticheg | test bet values and current stage'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind(self.game, self.users['barticheg'])
        assert [0, 5, 10, 0] == [p.bet_total for p in self.game.players]
        assert self.game.stage.__class__.__name__ == 'BiddingsStage-1'

        test = '[5] PlaceBlind by vybornyy | test raises when game has another stage'
        logger.info(StrColors.purple(test))
        match = r'Acting .* failed. ' r'Game has another current stage: BiddingsStage-1'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBlind(self.game, self.users['vybornyy'])

    def test_invalid_bet_values(self, setup_users_banks: list[int]):
        actions.StartAction(self.game, self.users['vybornyy'])

        test = (
            '[1] PlaceBet by simusik with invalid value 10, but expectd 5 (small blind)'
        )
        logger.info(StrColors.purple(test))
        condition_name = 'value_in_valid_range_condition'
        match = r'Acting .* failed. ' rf'Condition {condition_name} are not satisfied'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBet(self.game, self.users['simusik'], value=10)
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[2] PlaceBet by simusik with valid value. It`s okey, if act PlaceBet when expected PlaceBlind. '
        logger.info(StrColors.purple(test))
        actions.PlaceBet(self.game, self.users['simusik'], value=5)
        assert [0, 5, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[3] PlaceBlinds by barticheg to go ahead'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind(self.game, self.users['barticheg'])

        test = '[4] PlaceBet by arthur_morgan with invalid values'
        logger.info(StrColors.purple(test))

        condition_name = 'value_in_valid_range_condition'
        match = r'Acting .* failed. ' rf'Condition {condition_name} are not satisfied'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=0)

        condition_name = 'value_in_valid_range_condition'
        match = r'Acting .* failed. ' rf'Condition {condition_name} are not satisfied'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=10000)

        condition_name = 'It is not multiples of small blind'
        match = r'Acting .* failed. ' rf'.*{condition_name}.*'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBet(self.game, self.users['arthur_morgan'], value=13)

        # assert that players bank has not been changed
        assert (
            self.users['arthur_morgan'].profile.bank
            == self.input_users_bank['arthur_morgan']
        )

    def test_necessary_action_values(self, setup_users_banks: list[int]):
        actions.StartAction(self.game, self.users['vybornyy'])

        test = '[1] test necessary_action_values'
        logger.info(StrColors.purple(test))
        assert self.game.stage.get_necessary_action_values() == {'min': 5, 'max': 5}

        test = '[2] go ahead...'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind(self.game, self.users_list[1])
        actions.PlaceBlind(self.game, self.users_list[2])

        assert self.game.stage.get_necessary_action_values() == {
            'max': min(setup_users_banks),  # smallest opponents bank
            'min': DEFAULT.big_blind,  # biggets bet placed on the table
        }


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game', 'setup_users_banks')
class TestGameBetActions(BaseGameProperties):
    usernames = (
        'vybornyy',
        'simusik',
        'werner_herzog',
        'barticheg',
        'arthur_morgan',
    )
    input_users_bank: dict[str, int]

    @property
    def players_bets_total(self):
        return [p.bet_total for p in self.game.players.active]

    def test_place_bet_all_actions_and_pass_action(self):
        """This test has assertion for:

        PlaceBet
        PlaceBetVaBank
        PlaceBetCheck
        PlaceBartReply
        PassAction
        """
        actions.StartAction(self.game, self.users['vybornyy'])

        # [1] - [4]
        test = '[1] PlaceBlind by simusik'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind(self.game, self.users['simusik'])

        test = '[2] Pass by werner_herzog'
        logger.info(StrColors.purple(test))
        actions.PassAction(self.game, self.users['werner_herzog'])

        test = '[3] PlaceBlind by barticheg -- raises. See rule [Blind Fixed to Player]'
        logger.info(StrColors.purple(test))
        with pytest.raises(actions.ActError, match=r'Game has another current stage'):
            actions.PlaceBlind(self.game, self.users['barticheg'])

        test = '[4] PlaceBet by barticheg'
        logger.info(StrColors.purple(test))
        actions.PlaceBet(self.game, self.users['barticheg'], value=10)

        # [5] test place bet stage
        logger.info(StrColors.purple('[5] test place bet'))
        assert self.game.stage.performer == self.players['arthur_morgan']
        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-1'
        assert self.game.stage.necessary_action == 'PlaceBet'
        assert [0, 5, 10, 0] == self.players_bets_total

        # [6] test trying another player place bet
        logger.info(StrColors.purple('[6] trying another player place bet -- raises'))
        match = (
            r'Acting .* failed. '
            r'Game waiting for act from another player: .* arthur_morgan'
        )
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBet(self.game, self.users['simusik'], 25)

        # [7]
        logger.info(StrColors.purple('[7] test 2 remainig players place a valid bet.'))
        actions.PlaceBet(self.game, self.users['arthur_morgan'], 25)
        actions.PlaceBet(self.game, self.users['vybornyy'], 25)
        assert [25, 5, 10, 25] == self.players_bets_total

        # [8]
        test = '[8] next biddings circle. Match bet values. Game processing ahead to next BiddingStage'
        logger.info(StrColors.purple(test))
        actions.PlaceBet(self.game, self.users['simusik'], 20)
        actions.PlaceBet(self.game, self.users['barticheg'], 15)

        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-2'
        # assert there are no beds yet
        assert [0, 0, 0, 0] == self.players_bets_total
        # check that player after dealer is a first bet maker
        assert self.game.stage.performer == self.players['simusik']

        # [9]
        test = '[9] simusik say "check" (Zero bet will be placed)'
        logger.info(StrColors.purple(test))
        actions.PlaceBetCheck(self.game, self.users['simusik'])

        # [10]
        test = '[10] barticheg say "VaBank"'
        logger.info(StrColors.purple(test))
        actions.PlaceBetVaBank(self.game, self.users['barticheg'])
        expected = self.input_users_bank['vybornyy'] - 25
        assert expected == self.players['barticheg'].bet_total

        # [11]
        test = (
            '[11] arthur_morgan trying say "check" when there are other bet were placed'
        )
        logger.info(StrColors.purple(test))
        condition_name = 'value_in_valid_range_condition'
        match = rf'Condition {condition_name} are not satisfied'
        with pytest.raises(actions.ActError, match=match):
            actions.PlaceBetCheck(self.game, self.users['arthur_morgan'])

        # [12]
        test = '[12] arthur_morgan say pass | test that he is out of game now'
        logger.info(StrColors.purple(test))
        actions.PassAction(self.game, self.users['arthur_morgan'])
        assert self.players['arthur_morgan'].is_active is False
        assert self.game.stage.performer == self.players['vybornyy']

        # [13]
        test = '[13] vybornyy say pass'
        logger.info(StrColors.purple(test))
        actions.PassAction(self.game, self.users['vybornyy'])
        expected = [self.players['simusik'], self.players['barticheg']]
        assert expected == list(self.game.players.active)

        # [14]
        test = '[14] simusik say reply | test game go ahead to next stage'
        logger.info(StrColors.purple(test))
        actions.PlaceBetReply(self.game, self.users['simusik'])

        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-3'

        # [15]
        test = (
            '[15] simusik and barticheg say check twice | '
            'test game go ahead to the end and stop processing at SetUpStage (waiting for new round starting)'
        )
        logger.info(StrColors.purple(test))

        actions.PlaceBetCheck(self.game, self.users['simusik'])
        actions.PlaceBetCheck(self.game, self.users['barticheg'])
        # assert stage type
        assert str(self.game.stage) == 'BiddingsStage-4(final)'

        actions.PlaceBetCheck(self.game, self.users['simusik'])
        actions.PlaceBetCheck(self.game, self.users['barticheg'])
        # assert stage type
        assert str(self.game.stage) == 'SetupStage'
