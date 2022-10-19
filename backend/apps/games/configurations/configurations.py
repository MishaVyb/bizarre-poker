import os

import pydantic
from django.db import models

class ConfigSchema(pydantic.BaseModel):
    name: str = ''

    small_blind: int
    big_blind: int
    bet_multiplicity: int
    deck_shuffling: bool
    deck_container_name: str

    deal_cards_amount: int
    flops_amounts: list[int]
    jokers_amount: int
    multy_decks_amount: int

class ConfigChoices(models.TextChoices):
    BIZARRE = 'bizarre'
    FOOLISH = 'foolish'
    CLASSIC = 'classic'
    CRAZY = 'crazy'


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, 'setups')
CONFIG_FILES = {
    name: os.path.join(CONFIG_DIR, f'{name}.json') for name, verbose in ConfigChoices.choices
}
CONFIG_SCHEMAS = {
    name: ConfigSchema.parse_file(file) for name, file in CONFIG_FILES.items()
}

for name, schema in CONFIG_SCHEMAS.items():
    schema.name = name