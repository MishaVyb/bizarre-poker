import pydantic

class ConfigSchema(pydantic.BaseModel):
    small_blind: int
    big_blind: int
    bet_multiplicity: int
    deck_shuffling: bool
    deck_container_name: str


DEFAULT = ConfigSchema.parse_file('configurations.json')
