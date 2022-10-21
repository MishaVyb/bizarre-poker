import logging
from pprint import pformat
from re import A
from typing import Type

import pydantic
import pytest
from core.utils import JSON, init_logger, temporally
from core.utils.functools import change_loggers_level
from games.configurations.configurations import CONFIG_SCHEMAS, DEFAULT_CONFIG, GameConfig, get_config_schemas
from games.models.game import Game
from games.services.processors import AutoProcessor

from tests.tools import param_kwargs, param_kwargs_list

logger = init_logger(__name__)


@pytest.fixture(
    params=[
        param_kwargs(
            data={'name': [12, 13, 14]},
            exception=ValueError,
        ),
        param_kwargs(
            data={'small_blind': 999, 'big_blind': 0},
            exception=ValueError,
        ),
    ]
)
def monkeypath_parse_file(request, monkeypatch):
    json, exception = request.param.values()

    def mockreturn(*args, **kwargs):
        return GameConfig.parse_obj(json)

    monkeypatch.setattr(pydantic.BaseModel, 'parse_file', mockreturn)
    return json, exception


def test_get_config_schemas_rises(monkeypath_parse_file: tuple[JSON, Type[Exception]]):
    json, exception = monkeypath_parse_file

    with pytest.raises(exception):
        get_config_schemas(raises=True)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'config_name',
    [
        'default',
        'foolish',
        'classic',
        'cheeky',
        'bizarre',
    ],
)
def test_configurations_setups(simple_game: Game, config_name):
    # [1] check that no rises and get our point config
    test_config = get_config_schemas(raises=True)[config_name]

    # [2] make sure that game processing do not falls down
    change_loggers_level(logging.ERROR)
    with temporally(CONFIG_SCHEMAS, classic=test_config):
        AutoProcessor(simple_game, stop_after_rounds_amount=40).run()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'data',
    [
        param_kwargs_list(
            '[01] example from README.md',
            data={"stages": ["DealCardsStage", "OpposingStage"], "deal_cards_amount": 5, "jokers_amount": 10},
        ),
    ],
)
def test_configurations_examples(data: JSON, simple_game: Game):
    schema = GameConfig.parse_obj(data)
    logger.info('\n' + pformat(schema) + '\n')

    with temporally(CONFIG_SCHEMAS, classic=schema):
        AutoProcessor(simple_game, stop_after_rounds_amount=2).run()


@pytest.mark.xfail
def test_get_json_schema():
    logger.info('\n' + pformat(DEFAULT_CONFIG.schema()) + '\n')
