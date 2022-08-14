"""

developing:
[ ] чтобы не надо было вызывать save() каждый раз
[ ] все константы перенести в файл настроек (json файл) и подгружать их с помошью библиотеки для парсинга

"""

from __future__ import annotations

import itertools
from django.db.models import Q
import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Optional
from django.core.exceptions import ValidationError
from core.functools.looptools import circle_after, looptools
from core.functools.utils import init_logger
from core.models import CreatedModifiedModel
from django.db import IntegrityError, models
from django.db.models import manager
from django.db.models.query import QuerySet
from django.urls import reverse
from games.backends.cards import CardList, Decks
from games.exeptions import PostRequestRequired
from games.models.fields import CardListField

if TYPE_CHECKING:
    from games.models import Player

from users.models import User
from django.core.handlers.wsgi import WSGIRequest

logger = init_logger(__name__, logging.INFO)


class Game(CreatedModifiedModel):
    SMALL_BLIND: int = 5
    BIG_BLIND: int = SMALL_BLIND * 2
    DECK_SHUFFLING = True

    deck: CardList = CardListField('deck of cards', blank=True)
    deck_generator: str = models.CharField(
        'name of deck generator method or contaianer',
        max_length=79,
        default='standart_52_card_deck_plus_jokers'
    )
    table: CardList = CardListField('cards on the table', blank=True)
    bank: int = models.PositiveIntegerField(
        'sum of all beds has maded for game round', default=0
    )

    # typing annotation for releted objects (handle it like combo: PlayerCombo)
    @property
    def players_manager(self) -> manager.RelatedManager:
        return self._players

    @property
    def players(self) -> QuerySet[Player]:
        return self.players_manager.all()

    @property
    def players_not_passed(self) -> QuerySet[Player]:
        return self.players_manager.filter(passed=False)

    @property
    def host(self) -> Player:
        return self.players_manager.get(host=True)

    @property
    def dealer(self) -> Player:
        return self.players_manager.get(dealer=True)


    action_name: str = models.CharField(max_length=30, default='setup')
    """key for GAME_ACTIONS dict"""

    @property
    def current_action(self) -> BaseGameAction:
        try:
            return GAME_ACTIONS[self.action_name]
        except KeyError as e:
            raise RuntimeError(f'Invalid action name: {e}')

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        # constraints = [
        #     models.CheckConstraint(
        #         check=~Q(host__count=1), name='only one host at game'
        #     )
        # ]

    def __init__(
        self,
        *args,
        deck: CardList = None,
        table: CardList = None,
        commit: bool = False,
        players: Iterable[User] = [],
    ) -> None:
        kwargs: dict[str, Any] = {}
        kwargs.setdefault('deck', deck) if deck is not None else ...
        kwargs.setdefault('table', table) if table is not None else ...

        assert not (
            kwargs and args
        ), f'not supported args and kwargs toogether. {args=}, {kwargs=}'

        super().__init__(*args, **kwargs)

        if commit:
            self.save()

        assert not players if not commit else True, (
            'django obligates to save a model instance'
            'before using it in related relashinships'
        )
        for user in players:
            try:
                # Player(user=user, game=self).save()
                self.players_manager.create(user=user, game=self)
            except IntegrityError as e:
                raise ValueError(f'{user} already playing in {self}: {e}')

    def __str__(self) -> str:
        return f'({self.pk}) game at {self.action_name}'

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})

    def clean(self) -> None:
        logger.info(f'clean {self} processing...')

        # CLEAN GAME
        ...

        # CLEAN PLAYERS DEPENDENCES
        if not self.players.exists():
            logger.info('Nothing to clean. Game has no players. ')
            return

        # Player is not defind because not imported (because circular import),
        # so there are a little trick
        Player = self.players.first().__class__

        # check host
        try:
            self.host
        except Player.DoesNotExist as e:
            raise ValidationError(f'No host at game: {e}')
        except Player.MultipleObjectsReturned as e:
            raise ValidationError(f'Many hosts at game: {e}')

        # chek dealer
        try:
            self.dealer
        except Player.DoesNotExist as e:
            logger.info(f'Game has no dealer. Host becomes it. ')
            self.host.update(dealer=True)
        except Player.MultipleObjectsReturned as e:
            raise ValidationError(f'Many dealers at game: {e}')

        # chek players positions
        for i, player in enumerate(self.players):
            if player.position is None:
                logger.info(f'{player} position is None. Make it {i}. ')
                player.position = i
                player.save()
        # ckeck players positions finaly
        positions = [p.position for p in self.players]
        if list(range(self.players.count())) != positions:
            raise ValidationError(f'Invalid players positions: {positions}')









    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:



        # pk is None for first game saving (just after creation)
        # so validation won't work because of failing ralated ForigenKey fields
        if self.pk:
            self.full_clean()

        return super().save(force_insert, force_update, using, update_fields)

    # ------- game iterations default implementations -------
    def continue_processing(self):
        # before proccesiign call clean
        self.full_clean()

        for _ in range(len(GAME_ACTIONS)):
            self.current_action.game = self
            self.current_action.pre_call()
            self.current_action()
            self.current_action.post_call()
        else:
            raise RuntimeError('Continue processing reached the end.')

    def again(self):
        assert (
            self.step != self._meta.get_field('step').default
        ), f'calling again for not played game at all: {self.step=}'
        self.step = self._meta.get_field('step').default

    # ------------------------------------------------------------------------------


class BaseGameAction:
    """Base class for describing one game action.

    After execution game action is defined as next action and save game model.
    """

    game: Game | None = None
    requirements: list[BaseActionRequirement] = []

    def __init__(self, name: str) -> None:
        self.name = name
        pass

    def pre_call(self):

        logger.debug(f'check requirements for "{self}"...')
        for requirement in self.requirements:
            requirement.game = self.game
            requirement()

        logger.info(f'start processing "{self}"...')

    def __call__(self):
        raise NotImplementedError

    def post_call(self):
        new = next(
            circle_after(
                lambda a: a == self.game.action_name, GAME_ACTIONS, inclusive=False
            )
        )
        self.game.action_name = new
        self.game.save()
        logger.debug(f'end processing "{self}"...')

    def __str__(self) -> str:
        return self.name


class BaseActionRequirement:
    _satisfyed = False
    game: Game | None = None

    @property
    def satisfyed(self):
        if self._satisfyed:
            self._satisfyed = False
            return True
        return False

    def satisfy(self):
        assert not self._satisfyed, 'already satysfyed'
        self._satisfyed = True
        logger.debug(f'Set {self._satisfyed=} for {self}')

    def __call__(self):
        raise NotImplementedError

    def __str__(self) -> str:
        return f'Requirement {self.__class__.__name__}'

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, BaseActionRequirement):
            return type(self) == type(__o)
        elif isinstance(__o, type):
            return type(self) == __o
        return NotImplemented


class RequirementError(Exception):
    def __init__(
        self,
        messsage: str,
        requirement: BaseActionRequirement,
        satisfier: Player,
        *args: object,
    ) -> None:
        self.message = messsage
        self.requirement = requirement
        self.satisfier = satisfier
        super().__init__(*args)

    def __str__(self) -> str:
        return f'{self.requirement} not sytisfyed: {self.message}'


class HostApprovedGameStart(BaseActionRequirement):
    def __call__(self):
        if not self.satisfyed:
            host = self.game.players_manager.get(host=True)
            raise RequirementError(
                f'Host {host} should aprrove new game starting', self, host
            )

        logger.info(f'{self} requirement has sytesfied. ')


class AllPlayersPlaceBeds(BaseActionRequirement):
    def __call__(self):
        filtered = self.game.players_manager.filter(_bet__value=None)
        if filtered.exists():
            player = filtered.first()
            raise RequirementError(
                f'{player} should make a bet or say "pass"', self, player
            )
        logger.info(f'{self} requirement has sytesfied. ')


class AllPlayersBedsEqual(BaseActionRequirement):
    def __call__(self):
        active_bet_value = self.game.players_not_passed.first().bet.value
        for player in self.game.players_not_passed:
            if not player.bet.value == active_bet_value:
                raise RequirementError(
                    f'{player} should make a bet or say "pass"', self, player
                )

        logger.info(f'{self} requirement has sytesfied. ')


# -----------------------------------------------------------------------------------------------


class SetUp(BaseGameAction):
    """Prepare new round."""

    requirements = [HostApprovedGameStart()]

    def __call__(self):
        self.fill_and_shuffle_deck()

    def fill_and_shuffle_deck(self):
        deck = getattr(Decks, self.game.deck_generator)

        if callable(deck):
            self.game.deck = CardList(instance=deck())
        elif isinstance(deck, CardList):
            self.game.deck = CardList(instance=deck)
        else:
            raise TypeError

        if Game.DECK_SHUFFLING:
            self.game.deck.shuffle()



class PlaceBlinds(BaseGameAction):
    def __call__(self):
        # we need cycle if 2 player at game (in that case Dealer placing BIG BLIND)
        it = itertools.cycle(self.game.players)
        dealer = next(it) # dealer
        _1st = next(it)
        _2nd = next(it)
        _1st.bet.place(Game.SMALL_BLIND)
        _2nd.bet.place(Game.BIG_BLIND)
        logger.info(f'placing blinds info: {dealer.bet.value=} | {_1st.bet.value=} | {_2nd.bet.value=}')




        # it: Iterator[Player] = circle_after(self.game.players, inclusive=False)
        # try:
        #     next(it).bet.place(self.game.SMALL_BLIND)
        #     next(it).bet.place(self.game.BIG_BLIND)
        # except StopIteration as e:
        #     count = self.game.players.count()
        #     logger.warning(f'Game has {count} players, which is not enough: {e}. ')


class AcceptBeds(BaseGameAction):
    requirements = [AllPlayersPlaceBeds(), AllPlayersBedsEqual()]

    def __call__(self):
        for player in self.game.players_not_passed:
            player.bet.accept()


class DealCards(BaseGameAction):
    """Pre-flop: draw cards to all players."""

    def __init__(self, name: str, deal_amount: int = 2) -> None:
        self.deal_amount = deal_amount
        super().__init__(name)

    def __call__(self):
        if any(p.hand for p in self.game.players):
            logger.warning(
                f'Player has cards in hand at {self}. '
                'Clear all players hands for continue. '
            )
            for p in self.game.players:
                p.hand.clear()
                p.save()

        for _ in range(self.deal_amount):
            for player in self.game.players:
                player.hand.append(self.game.deck.pop())
                player.save()


class Flop(BaseGameAction):
    """Place cards on the table."""

    def __init__(self, name: str, flop_amount) -> None:
        self.flop_amount = flop_amount
        super().__init__(name)

    def __call__(self):
        for _ in range(self.flop_amount):
            self.game.table.append(self.game.deck.pop())


class Opposing(BaseGameAction):
    def __call__(self):
        """track players combinations, compare them to yeach others and finding out
        the winner
        """
        self.track_combos()
        ...
        ...

    def track_combos(self):
        for player in self.game.players:
            player.combo.setup()


class TearDown(BaseGameAction):
    def __call__(self):
        self.game.table.clear()
        if self.game.bank:
            logger.warning('Game bank value should be equal 0. Make it.')
            self.game.bank = 0

        for player in self.game.players:
            player.hand.clear()
            player.combo.delete()

            if player.bet.value:
                logger.warning('Player bet value should be equal 0. Make it.')
                player.bet.value = 0
                player.bet.save()

            player.save()


class MoveDealerButton(BaseGameAction):
    def __call__(self):
        """and change all players posotion clockwise, because dealer is always at 0 positions"""

        # move dealer
        it = circle_after(lambda p: p.dealer, self.game.players)
        try:
            next(it).set_dealer(False)
            next(it).set_dealer(True)
        except ValueError as e:
            logger.warning(f'Game has no dealer: {e} First player becomes it. ')
            self.game.players.first().set_dealer(True)
        except StopIteration as e:
            logger.warning(f'Game has no players: {e}. ')

        # re-range all players positions
        for i, player in enumerate(circle_after(lambda p: p.dealer, self.game.players)):
            player.position = i
            player.save()

    # def round_execution(self):
    #     """Processing full game round iteration, all in one method.
    #     Call round_setup if necceassery.
    #     """
    #     ...

    # class GameIterator(models.Model):
    # game: Game = models.OneToOneField(
    #     Game, on_delete=models.CASCADE, related_name='_iteration'
    # )

    # text information


GAME_ACTIONS: OrderedDict[str, BaseGameAction] = OrderedDict()
GAME_ACTIONS['setup'] = SetUp('setup')
GAME_ACTIONS['place blinds'] = PlaceBlinds('place blinds')
GAME_ACTIONS['deal cards'] = DealCards('deal cards', 2)
GAME_ACTIONS['accept first beds'] = AcceptBeds('accept first beds')
GAME_ACTIONS['first flop'] = Flop('first flop', 3)
GAME_ACTIONS['accept second beds'] = AcceptBeds('accept second beds')
GAME_ACTIONS['second flop'] = Flop('second flop', 1)
GAME_ACTIONS['accept third beds'] = AcceptBeds('accept third beds')
GAME_ACTIONS['third flop'] = Flop('third flop', 1)
GAME_ACTIONS['accept final beds'] = AcceptBeds('accept final beds')
GAME_ACTIONS['opposing'] = Opposing('opposing')
GAME_ACTIONS['teardown'] = TearDown('teardown')

# actions for next game
GAME_ACTIONS['move dealer button'] = MoveDealerButton('move dealer button')
