from __future__ import annotations

from abc import abstractmethod
from typing import Any, OrderedDict, Protocol, TypeVar, Union, runtime_checkable

_JSON_SUPPORTED = str | int | bool | float | None | list | dict | OrderedDict

JSON_STRICT = Union[dict[str, _JSON_SUPPORTED], list[_JSON_SUPPORTED]]
"""Type that represents a JSON dict."""

JSON = dict[str, Any] | list[Any]
"""Type that represents a JSON dict."""

NONE_ATTRIBUTE = type('_NoneAttributeClass', (object,), {})
"""Class for represent absence of value at defaults. Wnen None can't be used. """

# [FIXME]
# class _NotProvidedClass:
#     """Class for represent absence of value at defaults. Wnen None can't be used."""
#     pass

NOT_PROVIDED = type('_NotProvidedClass', (object,), {})
"""Class for represent absence of value at defaults. Wnen None can't be used."""

@runtime_checkable
class Comparable(Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self: _CT, other: _CT) -> bool:
        pass


@runtime_checkable
class TotalComparableAbstract(Protocol):
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


_CT = TypeVar("_CT", bound=Comparable)
'CompareableType. Similar to SupportsRichComparisonT'
_TCT = TypeVar('_TCT', bound=TotalComparableAbstract)
'TutalCompareableType. Similar to SupportsRichComparisonT, but also supports equals. '
