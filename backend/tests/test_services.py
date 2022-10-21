from pprint import pformat
import pytest
from core.utils import Interval, StrColors, init_logger, is_sorted
from games.services import actions, stages
from games.services.combos import Combo

from games.services.processors import AutoProcessor, BaseProcessor
from users.models import User

from tests.base import BaseGameProperties
from tests.tools import param_kwargs_list

logger = init_logger(__name__)


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestGameStages(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    initial_users_bank: dict[str, int]

    def test_get_possible_values_for(self, setup_users_banks: list[int]):
        actions.StartAction.run(self.game, self.users['vybornyy'])

        test = '[1] test get_possible_values_for PlaceBlind is None'
        logger.info(StrColors.purple(test))
        values = self.game.stage.get_possible_values_for(actions.PlaceBlind)
        assert values is None

        test = '[2] go ahead... and test get_possible_values_for PlaceBet'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind.run(self.game, self.users_list[1])
        actions.PlaceBlind.run(self.game, self.users_list[2])

        values = self.game.stage.get_possible_values_for(actions.PlaceBet)
        assert values == Interval(
            min=self.game.config.big_blind,     # biggets bet placed on the table
            max=min(setup_users_banks),         # smallest opponents bank
            step=self.game.config.bet_multiplicity,
        )

    @pytest.mark.skip('[TODO] need to refactor')
    def test_get_possible_actions_at_biddings_stages(self):
        game = self.game

        test = '[1] test possible actions after placing blinds (at BiddingsStage_1)'
        logger.info(StrColors.purple(test))
        AutoProcessor(game, stop_before_stage=stages.BiddingsStage_1).run()
        expected_actions_classes = [
            actions.PlaceBet,
            # actions.PlaceBetCheck,    # not possbile: chalenging bet on the table
            actions.PlaceBetReply,
            actions.PlaceBetVaBank,
            actions.PassAction,
        ]
        result_action_classes = [
            proto.action_class for proto in game.stage.get_possible_actions()
        ]
        assert expected_actions_classes == result_action_classes


        test = '[2] test possible actions at BiddingsStage_2'
        logger.info(StrColors.purple(test))
        AutoProcessor(game, stop_before_stage=stages.BiddingsStage_2).run()
        expected_actions_classes = [
            actions.PlaceBet,
            actions.PlaceBetCheck,
            # actions.PlaceBetReply,    # not possbile: nothing to reply
            actions.PlaceBetVaBank,
            # actions.PassAction,       # not possbile: there are not bet chalenging
        ]
        result_action_classes = [
            proto.action_class for proto in game.stage.get_possible_actions()
        ]
        assert expected_actions_classes == result_action_classes


        test = '[3] test possible actions at BiddingsStage_3 after VaBank'
        logger.info(StrColors.purple(test))
        AutoProcessor(game, stop_before_stage=stages.BiddingsStage_1).run()
        bet = actions.PlaceBetVaBank.prototype(game, game.players[1])
        AutoProcessor(game, with_actions=[bet]).run()
        expected_actions_classes = [
            # actions.PlaceBet,         # not uniq: only one value for bet is possible
            # actions.PlaceBetCheck,    # not possbile: chalenging bet on the table
            actions.PlaceBetReply,
            # actions.PlaceBetVaBank,   # not possbile: the same to reply
            actions.PassAction,
        ]
        result_action_classes = [
            proto.action_class for proto in self.game.stage.get_possible_actions()
        ]
        assert expected_actions_classes == result_action_classes


    def test_start_stage_bank_less_then_big_blind(self):
        poorman = self.players['vybornyy']
        poorman.user.profile.bank = self.game.config.small_blind
        poorman.user.profile.save()


        # [1] start is not awailable
        with pytest.raises(actions.ActionError):
            actions.StartAction.run(self.game)

        # [2] and AutoProcessor not falls down
        AutoProcessor(self.game, stop_after_rounds_amount=1).run()


    def test_start_stage_one_player(self):
        self.game.players_manager.exclude(user=self.users['vybornyy']).delete()

        # [1] start is not awailable
        with pytest.raises(actions.ActionError):
            actions.StartAction.run(self.game)

        # [2] and AutoProcessor not falls down
        AutoProcessor(self.game, stop_after_stage=stages.OpposingStage).run()

    def test_flop_stage(self):
        # arrange
        AutoProcessor(self.game, stop_after_stage=stages.SetupStage).run()

        input_deck = self.game.deck.copy()
        draw_total = sum(self.game.config.deal_cards_amounts)
        start = len(self.usernames) * draw_total
        end = start + self.game.config.flops_amounts[0]
        expected_flop = list(reversed(input_deck))[start:end]

        AutoProcessor(self.game, stop_after_stage=stages.FlopStage_1).run()

        # assert
        assert self.game.table == expected_flop
        assert self.game.deck == input_deck[: len(input_deck) - end]

    def test_none_performer_when_requirement_is_satisfied(self):
        game = self.game
        bets = [
            # game.players[1] small blind (5)
            # game.players[2] big blind (10)
            # game.players[3] reply with 10
            # game.players[0] reply with 10
            # and finaly game.players[1] reply with 5
            actions.PlaceBetReply.prototype(game, game.players[1]),
        ]
        AutoProcessor(game, with_actions=bets).run()
        assert self.game.stage.check_requirements(raises=False)
        assert self.game.stage.performer is None

        # but after Base Processor runs game goes to the next Biddings Stage
        # and therefore there are performer already
        BaseProcessor(self.game).run()
        assert self.game.stage.performer == self.players_list[1]

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
        winners: set[User] = set()
        for rate_group in rate_groups:
            winners_indexes = rate_group
            winners = {self.users_list[i] for i in winners_indexes}
            winners = winners - passed_users  # filter out passed users
            if winners:
                break
            # if not (all potential winners have passed)
            # we will continue to the next rate group

        loosers = active_users - winners  # filter out winners

        # prepere expected loosing and winning values
        all_bets_together = len(active_users) * self.game.config.big_blind
        benefit = all_bets_together // len(winners) - self.game.config.big_blind
        loss = self.game.config.big_blind

        # prepare pass actioins
        game = self.game
        prepares: list[actions.ActionPrototype] = []
        for user in passed_users:
            pass_ = actions.PassAction.prototype(game, user.player_at(game))
            prepares.append(pass_)

        # Act: play game
        AutoProcessor(
            game,
            stop_after_stage=stages.OpposingStage,
            with_actions=prepares,
        ).run()
        assert [p.combo for p in self.players_list] == expected

        reloaded_winners: set[User] = set()
        for w in winners:
            reloaded_winners.add(User.objects.get(username=w.username))
        winners = reloaded_winners

        # Assert winners banks
        for winner in winners:
            bank = self.initial_users_bank[winner.username]
            assert winner.profile.bank == bank + benefit

        # Assert lissers banks
        for looser in loosers:
            bank = self.initial_users_bank[looser.username]
            assert looser.profile.bank == bank - loss

        # Assert passed banks (it won`t change)
        for passed in passed_users:
            bank = self.initial_users_bank[passed.username]
            assert passed.profile.bank == bank

    def test_move_dealer_button(self):
        # arragne:
        AutoProcessor(self.game, stop_before_stage=stages.TearDownStage).run()
        assert isinstance(self.game.stage, stages.TearDownStage)

        # assertion before act:
        for player, expected_position in zip(self.players_list, [0, 1, 2, 3]):
            assert player.position == expected_position

        # act:
        AutoProcessor(self.game, stop_after_stage=stages.TearDownStage).run()

        # assert:
        for player, expected_position in zip(self.players_list, [3, 0, 1, 2]):
            assert player.position == expected_position
        assert is_sorted(self.game.players, key='position')


    def test_game_actions_history(self):
        actions.StartAction.run(self.game)
        # 1- start action by user
        # 2- SetupStage
        # 3- DealCardsStage
        assert len(self.game.actions_history) == 3


@pytest.mark.django_db
@pytest.mark.usefixtures('setup_game')
class TestGameActions(BaseGameProperties):
    usernames = ('vybornyy', 'simusik', 'barticheg', 'arthur_morgan')
    initial_users_bank: dict[str, int]

    def test_start_action(self):
        # [1] test game stage before beginings
        logger.info(StrColors.purple('[1] test game stage before beginings'))

        # test begins flag
        assert self.game.begins is False

        # test who is performer, by default it should be host player
        # access through dinamic property "stage"
        assert self.game.stage.performer == self.players['vybornyy']

        # [2] test game stages processing has not raised any exeption
        # game just has stoped processing and wait till player act neccessart action
        logger.info(StrColors.purple('[2] test game stages processing no failers'))
        BaseProcessor(self.game).run()

        # [3] test NOT host press "start"
        logger.info(StrColors.purple('[3] test NOT host press "start'))
        with pytest.raises(actions.ActionError):
            actions.StartAction.run(self.game, self.users['simusik'])

        # [4]
        logger.info(StrColors.purple('[4] test host "start"'))
        actions.StartAction.run(self.game, self.users['vybornyy'])

    def test_place_blinds_action(self):
        actions.StartAction.run(self.game, self.users['vybornyy'])
        test = '[1] test there are no beds at beginings'
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[2] PlaceBlind by simusik | test beds values'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind.run(self.game, self.users['simusik'])
        assert [0, 5, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[3] PlaceBlind by vybornyy | test raises'
        logger.info(StrColors.purple(test))
        with pytest.raises(actions.ActionError):
            actions.PlaceBlind.run(self.game, self.users['vybornyy'])

        test = '[4] PlaceBlind by barticheg | test bet values and current stage'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind.run(self.game, self.users['barticheg'])
        assert [0, 5, 10, 0] == [p.bet_total for p in self.game.players]
        assert self.game.stage == stages.BiddingsStage_1

        test = '[5] PlaceBlind by vybornyy | test raises when game has another stage'
        logger.info(StrColors.purple(test))
        with pytest.raises(actions.ActionError):
            actions.PlaceBlind.run(self.game, self.users['vybornyy'])

    def test_action_rises(self, setup_users_banks: list[int]):
        actions.StartAction.run(self.game, self.users['vybornyy'])

        test = '[1] PlaceBet like PlaceBlind by simusik -- that action is forbiden, only PlaceBet is possbile'
        logger.info(StrColors.purple(test))
        with pytest.raises(actions.ActionError):
            actions.PlaceBet.run(self.game, self.users['simusik'], value=10)
        assert [0, 0, 0, 0] == [p.bet_total for p in self.game.players]

        test = '[2] go ahead...'
        logger.info(StrColors.purple(test))
        actions.PlaceBlind.run(self.game, self.users['simusik'])
        actions.PlaceBlind.run(self.game, self.users['barticheg'])

        test = '[3] PlaceBet by arthur_morgan with invalid values'
        logger.info(StrColors.purple(test))
        with pytest.raises(actions.ActionError):
            actions.PlaceBet.run(self.game, self.users['arthur_morgan'], value=0)

        with pytest.raises(actions.ActionError):
            actions.PlaceBet.run(self.game, self.users['arthur_morgan'], value=10000)

        with pytest.raises(actions.ActionError):  # not ActionError
            actions.PlaceBet.run(self.game, self.users['arthur_morgan'], value=13)

        # assert that players bank has not been changed
        assert (
            self.users['arthur_morgan'].profile.bank
            == self.initial_users_bank['arthur_morgan']
        )

    @property
    def players_bets_total(self):
        return [p.bet_total for p in self.game.players.active]

    # @pytest.mark.skip('test need refactoring! because of pass action at blind stage')
    def test_place_bet_all_actions_and_pass_action(self, setup_users_banks):
        """This test has assertion for:

        PlaceBet
        PlaceBetVaBank
        PlaceBetCheck
        PlaceBartReply
        PassAction
        """
        actions.StartAction.run(self.game, self.users['vybornyy'])
        actions.PlaceBlind.run(self.game, self.users['simusik'])
        actions.PlaceBlind.run(self.game, self.users['barticheg'])

        # [5] test place bet stage
        logger.info(StrColors.purple('[5] test place bet | test profile banks'))
        assert self.game.stage.performer == self.players['arthur_morgan']

        assert self.game.stage == stages.BiddingsStage_1
        assert [0, 5, 10, 0] == self.players_bets_total

        expected = self.initial_users_bank.copy()
        expected['simusik'] -= self.game.config.small_blind
        expected['barticheg'] -= self.game.config.big_blind
        expected = [expected[name] for name in self.usernames]
        assert [p.user.profile.bank for p in self.game.players] == expected

        # [6] test trying another player place bet
        logger.info(StrColors.purple('[6] trying another player place bet -- raises'))
        with pytest.raises(actions.ActionError):
            actions.PlaceBet.run(self.game, self.users['simusik'], value=25)

        # [7]
        logger.info(StrColors.purple('[7] test 2 remainig players place a valid bet.'))
        actions.PlaceBet.run(self.game, self.users['arthur_morgan'], value=25)
        actions.PlaceBet.run(self.game, self.users['vybornyy'], value=25)
        assert [25, 5, 10, 25] == self.players_bets_total

        # [8]
        test = '[8] next biddings circle. Match bet values. Game processing ahead to next BiddingStage'
        logger.info(StrColors.purple(test))
        actions.PlaceBet.run(self.game, self.users['simusik'], value=20)
        actions.PlaceBet.run(self.game, self.users['barticheg'], value=15)

        assert self.game.stage == stages.BiddingsStage_2
        # assert there are no beds yet
        assert [0, 0, 0, 0] == self.players_bets_total
        # check that player after dealer is a first bet maker
        assert self.game.stage.performer == self.players['simusik']

        # [9]
        test = '[9] simusik say "check" (Zero bet will be placed)'
        logger.info(StrColors.purple(test))
        actions.PlaceBetCheck.run(self.game, self.users['simusik'])

        # [10-11]
        test = '[10-11] barticheg say "VaBank"'
        logger.info(StrColors.purple(test))
        actions.PlaceBetVaBank.run(self.game, self.users['barticheg'])
        expected = self.initial_users_bank['vybornyy'] - 25
        assert self.players['barticheg'].bet_total == expected

        # [12]
        test = '[12] arthur_morgan say pass | test that he is out of game now'
        logger.info(StrColors.purple(test))
        actions.PassAction.run(self.game, self.users['arthur_morgan'])
        assert self.players['arthur_morgan'].is_active is False
        assert self.game.stage.performer == self.players['vybornyy']

        # [13]
        test = '[13] vybornyy say pass'
        logger.info(StrColors.purple(test))
        actions.PassAction.run(self.game, self.users['vybornyy'])
        expected = [self.players['simusik'], self.players['barticheg']]
        assert expected == list(self.game.players.active)

        # [14]
        test = '[14] simusik say reply | test game go ahead to next stage'
        logger.info(StrColors.purple(test))
        actions.PlaceBetReply.run(self.game, self.users['simusik'])

        assert self.game.stage == stages.BiddingsStage_3

        # [15]
        test = '[15] simusik and barticheg say check twice '
        logger.info(StrColors.purple(test))

        actions.PlaceBetCheck.run(self.game, self.users['simusik'])
        actions.PlaceBetCheck.run(self.game, self.users['barticheg'])
        assert self.game.stage == stages.BiddingsStage_4

        actions.PlaceBetCheck.run(self.game, self.users['simusik'])
        actions.PlaceBetCheck.run(self.game, self.users['barticheg'])
        assert self.game.stage == stages.TearDownStage
