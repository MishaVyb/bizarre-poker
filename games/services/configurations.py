import pydantic


class ConfigSchema(pydantic.BaseModel):
    small_blind: int
    big_blind: int
    bet_multiplicity: int
    deck_shuffling: bool
    deck_container_name: str

    deal_cards_amount: int
    flops_amounts: list[int]


DEFAULT = ConfigSchema.parse_file('configurations.json')
