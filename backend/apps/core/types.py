from typing import Any, OrderedDict, Type, TypeAlias, Union

_JSON_SUPPORTED = str | int | bool | float | None | list | dict | OrderedDict

JSON_FULL = Union[dict[str, _JSON_SUPPORTED], list[_JSON_SUPPORTED]]
"""Type that represents a JSON dict."""

JSON = dict[str, Any] | list[_JSON_SUPPORTED]
"""Type that represents a JSON dict."""

NONE_ATTRIBUTE = type('_NoneAttributeClass', (object,), {})
"""Class for represent absence of value at defaults. Wnen None can't be used. """


class _NotProvidedClass:
    """Class for represent absence of value at defaults. Wnen None can't be used. """
    pass

NOT_PROVIDED = _NotProvidedClass