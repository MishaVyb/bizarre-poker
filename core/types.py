from typing import Type, Union

_JSON_SUPPORTED = Type[str | int | bool | float | None | list | dict]

JSON = Union[dict[str, _JSON_SUPPORTED], list[_JSON_SUPPORTED]]
"""Type that represents a JSON dict."""

NONE_ATTRIBUTE = type('_NoneAttributeClass', (object,), {})
"""Object for represent absence of value at defaults. Wnen None can't be used. """
