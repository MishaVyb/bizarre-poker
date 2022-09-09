from games.services import configurations
from django.core.exceptions import ValidationError

def bet_multiplicity(value: int):
    devider = configurations.DEFAULT.bet_multiplicity
    if value % devider:
        raise ValidationError(
            f'Value error: {value}. It is not multiples of small blind. '
        )