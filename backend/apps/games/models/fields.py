from __future__ import annotations


from core.utils import temporally
from core.utils import init_logger, isinstance_items, split
from django.core.exceptions import ValidationError
from django.db import models


from games.services.cards import Card, CardList, Stacks

logger = init_logger(__name__)


def cardlist_default():
    return CardList()


def stacks_default() -> Stacks:
    return []


class CardListField(models.Field):
    description = 'list of cards represented as string, seperated by space symbol'

    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get('blank'):
            kwargs['default'] = cardlist_default
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value: str, expression, connection) -> CardList:
        """is calling for transfer data from db"""
        return self.to_python(value)

    def to_python(self, value: str | CardList) -> CardList:
        """Is calling for transfer data from `Forms` to `Python` scrypt.
        Do not create new CardList instance if it comes by attrubute.
        """
        if isinstance(value, str):
            try:
                return CardList(*value.split(' '))
            except ValueError as e:
                raise ValidationError(
                    [ValidationError(arg, code='invalid') for arg in e.args]
                )
        elif isinstance(value, CardList):
            return value
        else:
            raise TypeError(f'ivalid type: {type(value)} ({value=}) ')

    @temporally(Card.Text, str_method='eng_short_suit')
    def get_prep_value(self, value: CardList) -> str:
        """converting Python objects to query values"""
        # type cheking
        if not isinstance(value, CardList):
            raise TypeError(
                f'CardListField stores only CardList instances, not {type(value)}. ',
                f'{value=}. ',
            )
        # representation
        return str(value)


class StacksField(models.Field):
    description = (
        'list of lists of cards (stacks) represented as string, seperated by [] symbols'
    )

    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get('blank'):
            kwargs['default'] = cardlist_default
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value: str, expression, connection) -> Stacks:
        """is calling for transfer data from db"""
        return self.to_python(value)

    def to_python(self, value: str | Stacks) -> Stacks:
        """Is calling for transfer data from `Forms` to `Python` scrypt."""
        if isinstance(value, str):
            try:
                stacks = split(value, by_symbols='[]')
                return list(CardList(*cards.split(' ')) for cards in stacks)
            except ValueError as e:
                raise ValidationError(
                    [ValidationError(arg, code='invalid') for arg in e.args]
                )
        elif isinstance_items(value, list, CardList):  # Stack
            return value
        else:
            raise TypeError(f'ivalid type: {type(value)} ({value=}) ')

    @temporally(Card.Text, str_method='eng_short_suit')
    def get_prep_value(self, value: Stacks) -> str:
        """converting Python objects to query values"""
        # type cheking
        if not isinstance_items(value, list, CardList):
            raise TypeError(
                f'StacksField stores only list of CardList instances, '
                f'not {type(value)}. ',
                f'{value=}. ',
            )
        # representation
        stacks = [str(cards) for cards in value]
        return ('[' + ']['.join(stacks) + ']') if stacks else '[]'
