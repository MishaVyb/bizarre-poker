from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any, Iterable, Optional

from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.core.exceptions import ValidationError

from core.functools.decorators import temporally
from core.functools.utils import isinstance_items, split
from games.backends.cards import Card, CardList, Stacks
from core.functools.utils import init_logger


if TYPE_CHECKING:
    from games.models import PlayerBet

logger = init_logger(__name__, logging.INFO)

class BetField(models.PositiveIntegerField):
    pass

#     def clean(self, value: Any, model_instance: Optional[models.Model]) -> Any:
#         return super().clean(value, model_instance)

#     def validate(self, value: int, model_instance: Optional[PlayerBet]) -> None:
#         """Note: None value will never be passed here. It checks in clean_fields method."""
#         if model_instance is None:
#             raise NotImplementedError

#         logger.info(f'validation for {self} is processing..')
#         bet = model_instance

#         # [1] check game action is valid
#         r = bet.player.game.get_requirement()
#         if not r.requirement == AllPlayersPlaceBeds:
#             message = (
#                 f'Invalid game requirement for placing a bet: {r.requirement}. '
#                 f'Waiting for {AllPlayersPlaceBeds}. '
#             )
#             logger.warning(f'{message} ValidatioError will be raised. ')
#             raise ValidationError(
#                 message,
#                 code='Invalid requirement',
#             )

#         # [2] check player
#         if bet.player is r.satisfier:
#             pass


#         # [3] check value
#         user_bank = bet.player.user.profile.bank
#         if user_bank < value:
#             message = (
#                 f'Invalid bet value: {value}. Not enough money. '
#                 f'{bet.player.user} has only {user_bank} at bank account. '
#             )
#             logger.warning(f'{message} ValidatioError will be raised. ')
#             raise ValidationError(
#                 message,
#                 code='Not enough money',
#             )




#         return super().validate(value, model_instance)








class CardListField(models.Field):
    description = 'list of cards represented as string, seperated by space symbol'

    def __init__(
        self,
        verbose_name: Optional[str] = None,
        name: Optional[str] = None,
        primary_key: bool = False,
        # max_length: Optional[int] = None,
        # unique: bool = False,
        blank: bool = True,  # default defenition
        # null: bool = None,
        db_index: bool = None,
        rel=None,
        default: CardList = NOT_PROVIDED,
        editable: bool = None,
        serialize: bool = None,
        unique_for_date: Optional[str] = None,
        unique_for_month: Optional[str] = None,
        unique_for_year: Optional[str] = None,
        choices=None,
        help_text: str = None,
        db_column: Optional[str] = None,
        db_tablespace: Optional[str] = None,
        auto_created: bool = None,
        validators: Iterable = (),
        error_messages=None,
    ):
        """Default implementations:

        max_length is `None`
            not implemented other yet

        unique is `False`
            One exception is when a CharField has both unique=True and blank=True set.
        In this situation, null=True is required to avoid unique constraint violations
        when saving multiple objects with blank values.

        null is `False`
            In most cases, it is redundant to have two possible values for “no data;”
        the Django convention is to use the empty string, not NULL

        blank is `True`
            it could be False, but not provide default value as CardList() in that way

        default set as empty `CardList`
            if blank is True
        """
        max_length: Optional[int] = None
        unique: bool = False
        null: bool = False
        if blank and default is NOT_PROVIDED:
            default = CardList()
        assert default is NOT_PROVIDED or isinstance(default, CardList)

        super().__init__(
            verbose_name,
            name,
            primary_key,
            max_length,
            unique,
            blank,
            null,
            db_index,
            rel,
            default,
            editable,
            serialize,
            unique_for_date,
            unique_for_month,
            unique_for_year,
            choices,
            help_text,
            db_column,
            db_tablespace,
            auto_created,
            validators,
            error_messages,
        )

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

    def __init__(
        self,
        verbose_name: Optional[str] = None,
        name: Optional[str] = None,
        primary_key: bool = False,
        # max_length: Optional[int] = None,
        # unique: bool = False,
        blank: bool = True,  # default defenition
        # null: bool = None,
        db_index: bool = None,
        rel=None,
        default: CardList = NOT_PROVIDED,
        editable: bool = None,
        serialize: bool = None,
        unique_for_date: Optional[str] = None,
        unique_for_month: Optional[str] = None,
        unique_for_year: Optional[str] = None,
        choices=None,
        help_text: str = None,
        db_column: Optional[str] = None,
        db_tablespace: Optional[str] = None,
        auto_created: bool = None,
        validators: Iterable = (),
        error_messages=None,
    ):
        """Default implementations:

        max_length is `None`
            not implemented other yet

        unique is `False`
            One exception is when a CharField has both unique=True and blank=True set.
        In this situation, null=True is required to avoid unique constraint violations
        when saving multiple objects with blank values.

        null is `False`
            In most cases, it is redundant to have two possible values for “no data;”
        the Django convention is to use the empty string, not NULL

        blank is `True`
            it could be False, but not provide default value as CardList() in that way

        default set as empty `CardList`
            if blank is True
        """
        max_length: Optional[int] = None
        unique: bool = False
        null: bool = False
        if blank and default is NOT_PROVIDED:
            default = list()
        assert default is NOT_PROVIDED or isinstance_items(default, list, CardList)

        super().__init__(
            verbose_name,
            name,
            primary_key,
            max_length,
            unique,
            blank,
            null,
            db_index,
            rel,
            default,
            editable,
            serialize,
            unique_for_date,
            unique_for_month,
            unique_for_year,
            choices,
            help_text,
            db_column,
            db_tablespace,
            auto_created,
            validators,
            error_messages,
        )

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
        elif isinstance(value, Stacks):
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
