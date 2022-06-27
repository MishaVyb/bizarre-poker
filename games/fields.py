
from typing import Iterable
from django.db import models
from django.forms import ValidationError
from core.functools.decorators import temporary_globals
from core.functools.utils import isinstance_items, split

from games.backends.cards import Card, CardList, JokerCard, Stacks

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


class StacksField(models.Field):
    description = 'list of lists of cards (stacks) represented as string, seperated by [] symbols'

    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value: str, expression, connection) -> Stacks:
        """is calling for transfer data from db"""
        return self.to_python(value)

    def to_python(self, value: str | Stacks | None) -> Stacks:
        """Is calling for transfer data from `Forms` to `Python` scrypt.
        """
        # print('to_python', 'value = ', value, type(value))
        if isinstance(value, str):
            try:
                stacks = split(value, by_symbols='[]')
                return list(CardList(*cards.split(' ')) for cards in stacks)
            except ValueError as e:
                raise ValidationError(
                    [ValidationError(arg, code='invalid') for arg in e.args]
                )
        return value or list()

    @temporary_globals(
        Card__STR_METHOD=Card.Text.repr_as_eng_short_suit,
        JokerCard__STR_METHOD=JokerCard.Text.repr_as_eng_short_suit,
    )
    def get_prep_value(self, value: Stacks) -> str:
        """converting Python objects to query values"""
        # # print('get_prep_value')

        if not isinstance_items(value, CardList):
            raise TypeError(
                f'StacksField stores only list of CardList instances, not {type(value)}. ',
                f'{value=}. ',
            )

        stacks = [str(cards) for cards in value]
        represantation = ']['.join(stacks) if value else '[]'
        return represantation

