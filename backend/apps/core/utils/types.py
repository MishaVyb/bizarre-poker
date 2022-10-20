from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, OrderedDict, TypeVar, Union

import pydantic

_JSON_SUPPORTED = str | int | bool | float | None | list | dict | OrderedDict

JSON_STRICT = Union[dict[str, _JSON_SUPPORTED], list[_JSON_SUPPORTED]]
"""Type that represents a JSON dict."""

JSON = dict[str, Any] | list[Any]
"""Type that represents a JSON dict."""

NONE_ATTRIBUTE = type('_NoneAttributeClass', (object,), {})
"""Class for represent absence of value at defaults. Wnen None can't be used. """


# class _NotProvidedClass:
#     """Class for represent absence of value at defaults. Wnen None can't be used."""
#     pass
NOT_PROVIDED = type('_NotProvidedClass', (object,), {})
"""Class for represent absence of value at defaults. Wnen None can't be used."""


class ComparableAbstract(metaclass=ABCMeta):
    @abstractmethod
    def __lt__(self, other: Any) -> bool:
        ...


class TotalComparableAbstract(metaclass=ABCMeta):
    @abstractmethod
    def __lt__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __le__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __ne__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __ge__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __gt__(self, other: Any) -> bool:
        ...

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(
        cls, value: TotalComparableAbstract, field: pydantic.fields.ModelField
    ):
        """Pointless method to satisfy pydantic requirements for Arbitary Types."""
        return value


_SupportsRichComparison = TypeVar('_SupportsRichComparison', bound=ComparableAbstract)
_TotalComparable = TypeVar('_TotalComparable', bound=TotalComparableAbstract)
'Simple extension for SupportsRichComparison Type'
