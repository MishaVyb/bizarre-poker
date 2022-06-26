from __future__ import annotations

from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.urls import reverse
from core.functools.decorators import temporary_globals
from django.db.models import Q

from games.backends.cards import Card, JokerCard, CardList


class CardListField(models.Field):
    description = 'list of cards represented as string, seperated by space symbol'

    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value: str, expression, connection) -> CardList:
        """is calling for transfer data from db"""
        return self.to_python(value)

    def to_python(self, value: str | CardList | None) -> CardList:
        """Is calling for transfer data from `Forms` to `Python` scrypt.
        Do not create new CardList instance if it comes by attrubute.
        """
        # print('to_python', 'value = ', value, type(value))
        if isinstance(value, str):
            try:
                return CardList(*value.split(' '))
            except ValueError as e:
                raise ValidationError(
                    [ValidationError(arg, code='invalid') for arg in e.args]
                )
        return value or CardList()

    @temporary_globals(
        Card__STR_METHOD=Card.Text.repr_as_eng_short_suit,
        JokerCard__STR_METHOD=JokerCard.Text.repr_as_eng_short_suit,
    )
    def get_prep_value(self, value: CardList) -> str:
        """converting Python objects to query values"""
        # print('get_prep_value')
        if not isinstance(value, CardList):
            raise TypeError(
                f'CardListField stores only CardList instances, not {type(value)}. ',
                f'{value=}. ',
            )

        represantation = str(value)
        return represantation


User = get_user_model()
# ----> players


class Game(models.Model):
    deck = CardListField('deck of cards', default=CardList())
    table = CardListField('cards on the table', default=CardList())
    # ----> players

    class Meta:
        verbose_name = 'poker game'
        verbose_name_plural = 'poker games'
        # constraints = [
        #     models.CheckConstraint(check= (~Q(players_list=[])), name='not empty players list')
        # ]

    def players_list(self) -> list[Player]:
        return list(self.players.all())

    def get_absolute_url(self):
        return reverse("games:game", kwargs={"pk": self.pk})


    def __str__(self) -> str:
        return f'game {self.pk=}, {self.deck=}, {self.table=}'


class Player(models.Model):
    hand = CardListField('cards in players hand', blank=True)
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='players',
    )
    game = models.ForeignKey(to=Game, on_delete=models.CASCADE, related_name='players')

    class Meta:
        verbose_name = 'user in game'
        verbose_name_plural = 'users in games'
        constraints = [
            models.UniqueConstraint(  # User can play in Game only by one Player
                fields=['user', 'game'], name='unique'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user.username} plaing at {self.game.pk=}'
