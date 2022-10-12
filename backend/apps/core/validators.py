from django.core.exceptions import ValidationError

from core.functools.utils import isinstance_items


def bet_multiplicity(value: int):
    raise NotImplementedError
    # devider = DEFAULT.bet_multiplicity
    # if value % devider:
    #     raise ValidationError(
    #         f'Value error: {value}. It is not multiples of small blind. '
    #     )


def bet_multiplicity_list(value: list[int]):
    raise NotImplementedError
    # if not isinstance(value, list):
    #     raise ValidationError(f'Value error: {value}. It is not a list. ')
    # for bet in value:
    #     bet_multiplicity(bet)

def int_list_validator(value: list[int]):
    if not isinstance_items(value, list, int):
        raise ValidationError(f'Value error: {value}. It is not a list[int]. ')