from django.core.exceptions import ValidationError
from core.utils import isinstance_items


def int_list_validator(value: list[int]):
    if not isinstance_items(value, list, int):
        raise ValidationError(f'Value error: {value}. It is not a list[int]. ')
