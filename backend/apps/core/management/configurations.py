import sys

import pydantic


class ConfigSchema(pydantic.BaseModel):
    small_blind: int
    big_blind: int
    bet_multiplicity: int
    deck_shuffling: bool
    deck_container_name: str

    deal_cards_amount: int
    flops_amounts: list[int]
    jokers_amount: int
    multy_decks_amount: int

p = sys.path
tmp = {
    "small_blind": 5,
    "big_blind": 10,
    "bet_multiplicity": 5,
    "deck_shuffling": True,
    "deck_container_name": "full_deck_plus_jokers",

    "deal_cards_amount": 2,
    "flops_amounts": [3, 1, 1],
    "jokers_amount": 2,
    "multy_decks_amount": 1
}
DEFAULT = ConfigSchema.parse_obj(tmp)
#DEFAULT = ConfigSchema.parse_file('/games/management/default_config.json')
