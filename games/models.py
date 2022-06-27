from __future__ import annotations
from multiprocessing.dummy import current_process
from typing import Callable, ClassVar, Iterable, Iterator

from django.db import models
from django.contrib.auth import get_user_model

from django.urls import reverse
from core.functools.decorators import temporary_globals

from core.functools.utils import split

from games.backends.cards import Card, Decks, JokerCard, CardList
from games.backends.combos import ComboKind, ComboStacks
from games.fields import CardListField, StacksField


User = get_user_model()
# ----> players


class Game(models.Model):
    deck = CardListField('deck of cards', default=CardList())
    table = CardListField('cards on the table', default=CardList())
    # ----> players
    # deck_generator = default value for now

    class Meta:
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        # constraints = [
        #     models.CheckConstraint(check= (~Q(players_list=[])), name='not empty players list')
        # ]

    def __str__(self) -> str:
        return f'game {self.pk=}, {self.deck=}, {self.table=}'

    def players_list(self) -> list[Player]:
        return list(self.players.all())

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})

    # ------- game iterations default implementations -------
    def fill_and_shuffle_deck(self, generator=Decks.standart_52_card_deck_plus_jokers):
        self.deck = CardList(instance=generator())
        self.deck.shuffle()
        self.save()

    def deal_cards(self, deal_amount: int = 2):
        """draw cards to all players"""
        assert not any(
            p.hand for p in self.players.all()
        ), 'player can not has cards in hand'
        for _ in range(deal_amount):
            for player in self.players.all():
                player.hand.append(self.deck.pop())
                player.save()

        self.save()

    def flop(self, flop_amount: int):
        """place cards on the table"""
        for _ in range(flop_amount):
            self.table.append(self.deck.pop())
        self.save()

    def place_bets(self):
        ...

    def track_combos(self):
        for player in self.players.all():
            stacks = ComboStacks()
            kind = stacks.track_and_merge(player.hand, self.table)
            combo, is_new = PlayerCombo.objects.get_or_create(player=player)
            combo.setup(combo_kind=kind, combo_stacks=stacks)
            combo.save()

        # self.save() !!!!

    def opposing(self):
        """track players combinations, compare them to yeach others and finding out the winner"""
        self.track_combos()
        ...
        ...

    def setup_round(self):
        """call it between round executions"""
        self.fill_and_shuffle_deck()
        self.table.clear()
        self.save()

        for player in self.players.all():
            player.hand.clear()
            player.save()

    def round_execution(self):
        """Processing full game round iteration, all in one method.
        Call round_setup if necceassery.
        """
        ...


class GameProcess(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name='process')

    # text information
    status = models.CharField(max_length=79, default='not define yet')
    info = models.CharField(max_length=200, default='not define yet')

    step = models.SmallIntegerField(default=0)
    """index for methods list"""
    methods: ClassVar = [
        'setup_round',
        'place_bets',
        'deal_cards(2)',
        'place_bets',
        'flop(3)',
        'place_bets',
        'flop(1)',
        'place_bets',
        'flop(1)',
        'place_bets',
        'opposing',
    ]

    def __next__(self):
        try:
            current = self.methods[self.step]
        except IndexError:
            raise StopIteration('end of game round (no more methods to be exicuted)')

        splitted = split(current)
        current = splitted[0]
        args = [int(arg) for arg in splitted[1:]]
        execution: Callable[[], None] = getattr(self.game, current)
        execution(*args)

        self.status = f'execution: {current} with {args=}'

        if current == 'opposing':
            self.info = ' | '.join(
                [str(p) + ' combo: ' + str(p.combo) for p in self.game.players.all()]
            )

        self.step += 1
        self.save()


class Player(models.Model):
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='players',
    )
    game = models.ForeignKey(to=Game, on_delete=models.CASCADE, related_name='players')
    hand = CardListField('cards in players hand', blank=True)
    # ---> combo: PlayerCombo = None

    class Meta:
        verbose_name = 'user in game (player)'
        verbose_name_plural = 'users in games (players)'
        constraints = [
            models.UniqueConstraint(  # User can play in Game only by one Player
                fields=['user', 'game'], name='unique'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username}'


class PlayerCombo(models.Model):
    player = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='combo'
    )
    name = models.CharField(max_length=20, blank=True)

    # cases
    rank = StacksField(default=[])
    suit = StacksField(default=[])
    row = StacksField(default=[])
    highest_card = StacksField(default=[])

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

    def setup(self, combo_kind: ComboKind = None, combo_stacks: ComboStacks = None):
        if combo_kind:
            #assert not self.name
            self.name = combo_kind.name
        if combo_stacks:
            #assert not any([self.rank, self.suit, self.row, self.highest_card])
            self.rank = combo_stacks.cases.get('rank', [])
            self.suit = combo_stacks.cases.get('suit', [])
            self.row = combo_stacks.cases.get('row', [])
            self.highest_card = combo_stacks.cases.get('highest_card', [])

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
