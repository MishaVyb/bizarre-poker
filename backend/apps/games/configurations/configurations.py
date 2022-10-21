from __future__ import annotations

import os
from typing import Callable, Iterable, Type

import pydantic
from core.utils import Interval, init_logger
from django.db import models
from games.services import stages as stages_module
from games.services.stages import SetupStage, TearDownStage
from games.services.cards import Card, CardList, Decks
from games.services.combos import ComboKind, ComboKindList

logger = init_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SETUPS_DIR = os.path.join(CURRENT_DIR, 'setups')


class ConfigChoices(models.TextChoices):
    BIZARRE = 'bizarre'
    CHEEKY = 'cheeky'
    FOOLISH = 'foolish'
    CLASSIC = 'classic'


class DeckConfig(pydantic.BaseModel):
    generator: Callable[[DeckConfig], Iterable[Card]] | CardList
    interval: Interval[Card]
    shuffling: bool
    jokers_amount: int
    iterations_amount: int

    class Config:
        allow_mutation = False

    @pydantic.validator('generator', pre=True)
    def _clean_generator(cls, generator: str | list):
        if isinstance(generator, list):
            return CardList(*generator)

        assert hasattr(Decks, generator)
        return getattr(Decks, generator)

    @pydantic.validator('interval', pre=True)
    def _clean_interval(cls, interval: list[str] | dict[str, str]):
        if isinstance(interval, dict):
            kwargs = {key: Card(value) for key, value in interval.items()}
            return Interval(**kwargs)

        assert isinstance(interval, list)
        assert len(interval) == 2
        return Interval(min=Card(interval[0]), max=Card(interval[1]))

    @pydantic.validator('iterations_amount')
    def _iterations_amount_not_null(cls, iterations_amount: int):
        assert (
            iterations_amount > 0
        ), 'null iterations amount has no sense, deck will be empty'
        return iterations_amount


class GameConfig(pydantic.BaseModel):
    name: str

    small_blind: int
    big_blind: int
    bet_multiplicity: int # by default equals to small_blind

    deck: DeckConfig

    deal_cards_amounts: list[int]
    flops_amounts: list[int]
    stages: list[str]

    combos: ComboKindList

    class Config:
        allow_mutation = False
        fields = {
            'stages': {'exclude': True},
            'deck': {'exclude': True},
            'combos': {'exclude': True},
            'bet_multiplicity': {'required': False}
        }

    @pydantic.validator('big_blind')
    def _big_blind_bigger_then_small_blind(cls, big_blind: int, values: dict):
        assert values['small_blind'] < big_blind
        return big_blind


    @pydantic.validator('bet_multiplicity')
    def _bets_are_multiple_for_bet_multiplicity(
        cls, bet_multiplicity: int, values: dict
    ):
        assert values['small_blind'] % bet_multiplicity == 0
        assert values['big_blind'] % bet_multiplicity == 0
        return bet_multiplicity

    @pydantic.validator('stages')
    def _clean_stages(cls, stages: list[Type[stages_module.BaseStage]]):
        if SetupStage in stages:
            assert stages.count(SetupStage) == 1, 'too many SetupStages'
            assert stages[0] == SetupStage, 'SetupStage should be first'
        else:
            stages.insert(0, SetupStage)
        if TearDownStage in stages:
            assert stages.count(TearDownStage) == 1, 'too many TearDownStages'
            assert stages[-1] == TearDownStage, 'TearDownStage should be last'
        else:
            stages.append(TearDownStage)
        return stages

    @pydantic.validator('stages', each_item=True)
    def _clean_stages_items(cls, stage: str):
        assert hasattr(stages_module, stage), f'that stage does not exist: {stage}'
        return getattr(stages_module, stage)

    @pydantic.validator('deal_cards_amounts', 'flops_amounts')
    def _amounts_retated_to_stages(
        cls, amounts: list[int], values: dict, field: pydantic.fields.ModelField
    ):
        return amounts
        # [TODO] get rid of stage number suffix and validate amounts here
        # ...
        # ...
        related_to = 'FlopStage' if field.name == 'flops_amounts' else 'DealCardsStage'
        assert len(amounts) == values['stages'].count(related_to)
        return amounts

    @pydantic.validator('combos')
    def _clean_combos(cls, combos: list[dict]):
        return ComboKindList([ComboKind(**combo) for combo in combos])


def get_config_schemas(*, raises: bool = False):
    # [1] set defaults for schemas:
    file = os.path.join(CURRENT_DIR, 'default.json')
    default = GameConfig.parse_file(file)
    for name, field in GameConfig.__fields__.items():
        field.required = False
        field.default = getattr(default, name)
    for name, field in DeckConfig.__fields__.items():
        field.required = False
        field.default = getattr(default.deck, name)

    # [2] load other setups:
    schemas = {'default': default}
    for name, verbose in ConfigChoices.choices:
        file = os.path.join(SETUPS_DIR, f'{name}.json')
        try:
            # set curent file name as default config name
            GameConfig.__fields__['name'].default = name
            # read config from file:
            schemas[name] = GameConfig.parse_file(file)
        except Exception as e:
            schemas[name] = GameConfig()
            if raises:
                raise e
            logger.warning(
                f'Invalid config file "{name}": {e}. '
                'Define all values for this configuration by default and continue. '
            )

    return schemas


CONFIG_SCHEMAS: dict[str, GameConfig] = get_config_schemas()
DEFAULT_CONFIG: GameConfig = CONFIG_SCHEMAS['default']
