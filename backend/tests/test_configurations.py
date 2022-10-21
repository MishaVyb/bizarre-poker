from pprint import pformat
from typing import Type

import pydantic
import pytest
from core.utils import init_logger
from games.configurations.configurations import GameConfig, get_config_schemas

from tests.tools import param_kwargs

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


def test_get_config_schemas_rises(monkeypath_parse_file: tuple[dict, Type[Exception]]):
    json, exception = monkeypath_parse_file

    with pytest.raises(exception):
        get_config_schemas(raises=True)


def test_configurations_setups():
    schemas = get_config_schemas(raises=True)
    for name, schema in schemas.items():
        logger.info(f'{name}:\n' + pformat(schema.dict()) + '\n')

    # [TODO] make assertions
    ...
