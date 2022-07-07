"""

developing:
[ ] чтобы не надо было вызывать save() каждый раз

"""


from __future__ import annotations

from typing import Any, Callable, Iterable, Reversible

from django.db import IntegrityError, models
from django.db.models.query import QuerySet
from django.db.models import manager
from django.urls import reverse
import itertools


from core.functools.looptools import lapafter, looptools
from games.backends.cards import CardList, Stacks, Decks
from games.backends.combos import ComboKind, ComboStacks
from games.fields import CardListField, StacksField

from core.models import CreatedModifiedModel


from users.models import User, UserModel


class Game(CreatedModifiedModel):
    deck: CardList = CardListField('deck of cards', blank=True)
    deck_generator = models.CharField(
        'name of deck generator method or contaianer',
        max_length=79,
        default='.'.join(
            [Decks.__name__, Decks.standart_52_card_deck_plus_jokers.__name__]
        ),
    )
    deck_generator_shuffling = True
    table: CardList = CardListField('cards on the table', blank=True)
    beds_storage: int = models.PositiveIntegerField(
        'sum of all beds maded for game round', default=0
    )

    SMALL_BLIND: int = 5
    BIG_BLIND: int = SMALL_BLIND * 2

    # typing annotation for releted objects (handle it like combo: PlayerCombo)
    @property
    def players(self) -> QuerySet[Player]:
        return self._players.all()

    @property
    def players_manager(self) -> manager.RelatedManager:
        return self._players

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'

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
                Player(user=user, game=self).save()
            except IntegrityError as e:
                raise ValueError(f'{user} already playing in {self}', *e.args)

    def __str__(self) -> str:
        return (
            f'({self.pk}): step[{self.step}] deck [...{self.deck[-5:]}], '
            f'table [{self.table}], {list(self.players)}'
        )

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})

    def clean(self) -> None:
        print(f'{self.clean.__name__} has called')
        return super().clean()

    # ------- game iterations default implementations -------

    def setup(self):
        """prepare round executions"""
        self.fill_and_shuffle_deck()
        self.move_dealer_button()

        # tmp
        for player in self.players:
            player.bet.append(0)

        self.get_blinds()
        self.save()

    def fill_and_shuffle_deck(self):
        full_deck = self.deck_generator

        # parsing from string:
        if isinstance(full_deck, str):
            splitted = full_deck.split('.')
            for attr, begins in looptools.begins(splitted):
                full_deck = globals()[attr] if begins else getattr(full_deck, attr)

        if callable(full_deck):
            self.deck = CardList(instance=full_deck())
        elif isinstance(full_deck, Iterable):
            self.deck = CardList(instance=full_deck)
        else:
            raise TypeError

        if self.deck_generator_shuffling:
            self.deck.shuffle()
        self.save()

    def move_dealer_button(self):
        # <re-code> by cycle method
        for loop in looptools(self.players):
            if loop.item.dealer:
                loop.item.dealer = False
                loop.item.save()
                if loop.has_following:
                    loop.following.dealer = True
                    loop.following.save()
                else:
                    loop.first.dealer = True
                    loop.first.save()
                break
            elif loop.final:
                # in case there are no dealer at all
                self.players.first().dealer = True
                self.players.first().save()

    # def players_clockwise(self, start=0, length=None, infinity=False):
    #     length = self.players.count()
    #     index = start
    #     stop = start - 1 if start > 0 else length - 1
    #     while True:
    #         try:
    #             yield self.players[index]
    #             index += 1
    #         except IndexError:
    #             index = 0

    def get_blinds(self):
        for i, player in zip([0, 1], lapafter(lambda p: not p.dealer, self.players)):
            p: Player = player
            p.bet.append(self.SMALL_BLIND if not i else self.BIG_BLIND)


    def ask_for_beds(self):
        self.players_manager.order_by('bet__modified').last()



    def deal_cards(self, deal_amount: int = 2):
        """pre-flop: draw cards to all players"""
        assert not any(p.hand for p in self.players), 'player can not has cards in hand'
        for _ in range(deal_amount):
            for player in self.players:
                player.hand.append(self.deck.pop())
                player.save()

        self.save()

    def flop(self, flop_amount: int):
        """place cards on the table"""
        for _ in range(flop_amount):
            self.table.append(self.deck.pop())
        self.save()

    def track_combos(self):
        for player in self.players:
            player.combo.setup()

    def opposing(self):
        """track players combinations, compare them to yeach others and finding out
        the winner
        """
        # self.track_combos()
        ...
        ...

    def teardown(self):
        self.table.clear()
        for player in self.players:
            player.hand.clear()
            player.combo.delete()
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
    status: str = models.CharField(max_length=50, default='not define yet')
    info: str = models.CharField(max_length=200, default='not define yet')

    step: int = models.SmallIntegerField(default=0)
    """index for methods list"""
    methods: list[tuple[str, list]] = [
        ('setup', []),
        ('deal_cards', [2]),
        ('flop', [3]),
        ('flop', [1]),
        ('flop', [1]),
        ('opposing', []),
        ('teardown', []),
    ]

    @property
    def current_action(self) -> tuple[str, list]:
        try:
            return self.methods[self.step]
        except IndexError:
            raise StopIteration('end of game round (no more methods to be exicuted)')

    @property
    def current_action_name(self) -> str:
        try:
            return self.methods[self.step][0]
        except IndexError:
            raise StopIteration('end of game round (no more methods to be exicuted)')

    def again(self):
        assert (
            self.step != self._meta.get_field('step').default
        ), 'calling again for not played game at all, because step equals default'
        self.step = self._meta.get_field('step').default

    # def __iter__(self):
    #     return self

    def __next__(self) -> tuple[int, str]:
        name, args = self.current_action

        execution: Callable[[], None] = getattr(self, name)
        execution(*args)

        self.status = f'execution: {name} with {args=}'

        self.track_combos()  # track it at every step jast for info

        self.info = ''.join(
            ['<p>' + str(p) + ' combo: ' + str(p.combo) + '</p>' for p in self.players]
        )

        self.step += 1
        self.save()

        return self.step, name


class Player(CreatedModifiedModel):
    """Model for representing single user at curtain game."""

    user: User = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='_players',
    )
    game: Game = models.ForeignKey(
        to=Game, on_delete=models.CASCADE, related_name='_players'
    )
    hand: CardList = CardListField('cards in players hand', blank=True)
    dealer: bool = models.BooleanField('dealer botton', default=False)
    """A dealer button is used to represent the player in the dealer position;
    the dealer button rotates clockwise after each round, changing the position of the
    dealer and blinds.
    """

    # typing annotation for releted objects (handle it like combo: PlayerCombo)
    @property
    def bet(self) -> PlayerBet:
        if hasattr(self, '_bet'):
            return self._bet
        return PlayerBet.objects.create(player=self)

    @property
    def combo(self) -> PlayerCombo:
        if hasattr(self, '_combo'):
            return self._combo
        return PlayerCombo.objects.create(player=self)

    # @property
    # def dealer(self) -> bool:
    #     return self._dealer

    # @dealer.setter
    # def dealer(self, value: bool):
    #     self._dealer = value
    #     self.save()

    # @property
    # def bet(self) -> bool:
    #     return self._bet

    # @bet.setter
    # def bet(self, value: bool):
    #     self._bet = value
    #     self.save()

    # def __setattr__(self, __name: str, __value: Any) -> None:
    #     super().__setattr__(__name, __value)
    #     self.save()

    def __init__(
        self,
        *args,
        user: User = None,
        game: Game = None,
        hand: CardList = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        kwargs.setdefault('user', user) if user else ...
        kwargs.setdefault('game', game) if game else ...
        kwargs.setdefault('hand', hand) if hand else ...
        assert not (
            kwargs and args
        ), f'not supported args and kwargs toogether. {args=}, {kwargs=}'
        super().__init__(*args, **kwargs)

    class Meta(CreatedModifiedModel.Meta):
        verbose_name = 'user in game (player)'
        verbose_name_plural = 'users in games (players)'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'game'],
                name='unique: User can play in Game only by one Player',
            ),
            # models.???Constraint(
            #     fields=['dealer'],
            #     name='only one dealer could be and it has to be',
            # )
            # models.UniqueConstraint(
            #     fields=['created'],
            #     name='it should be unique becase of proper ordering',
            # )
        ]

    def __str__(self) -> str:
        return f'({self.pk}) {self.user.username}: hand [{self.hand}]'




class PlayerBet(CreatedModifiedModel):
    """Current players bet. After beds applyed it becomes 0."""

    player: Player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='_bet'
    )
    # maker: bool = models.BooleanField('making a bet now', default=False)
    # """True if game is wating till this player append a bet."""
    value: int = models.PositiveIntegerField(default=0)


    class Meta(CreatedModifiedModel.Meta):
        pass

    def append(self, value: int):
        """appending a bet to the game. `user bank -= value` `bet += value`"""
        t = type(self.player.user)
        if value > self.player.user.profile.bank:
            raise NotImplementedError

        self.player.user.profile.bank -= value
        self.player.user.profile.save()

        self.value += value
        self.save()


class PlayerCombo(models.Model):
    player: Player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='_combo'
    )

    # combo kind name
    name: str = models.CharField(max_length=20, default='<not tracked yet>')
    priority: float = models.FloatField(blank=True, null=True)

    # combo stacks cases
    rank = StacksField()
    suit = StacksField()
    row = StacksField()
    highest_card = StacksField()

    def __init__(self, *args, player: Player = None) -> None:
        kwargs: dict[str, Any] = {}
        kwargs.setdefault('player', player) if player else ...
        super().__init__(*args, **kwargs)

    def __getitem__(self, key: str) -> Stacks:
        if key in ComboKind.CONDITION_KEYS:
            if hasattr(self, key):
                return getattr(self, key)
            raise RuntimeError
        raise KeyError

    def setup(self):
        # if self.name is not '<not tracked yet>':
        #     print("raise Warning('calling setup for already initialized combo')")
        stacks = ComboStacks()
        kind = stacks.track_and_merge(self.player.hand, self.player.game.table)

        if kind is None:
            self.name = '<no combination found>'
            self.save
        else:
            self.priority = kind.priority
            self.name = kind.name

            self.rank = stacks.cases.get('rank', [])
            self.suit = stacks.cases.get('suit', [])
            self.row = stacks.cases.get('row', [])
            self.highest_card = stacks.cases.get('highest_card', [])

            self.save()

    def __str__(self) -> str:
        return (
            self.name
            + ': '
            + (str(self.rank) if self.rank else '')
            + (str(self.suit) if self.rank else '')
            + (str(self.row) if self.rank else '')
            + (str(self.highest_card) if self.rank else '')
        )
