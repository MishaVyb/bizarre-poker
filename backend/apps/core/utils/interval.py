from __future__ import annotations

from typing import Generic, Iterable

from core.utils.types import _TotalComparable
from pydantic import validator
from pydantic.generics import GenericModel


class Interval(GenericModel, Generic[_TotalComparable]):
    """
    Interval represents value range (both `[min, max]` inclusevly).
    If `step` is provided, it should be a multiplier for `min` and `max`.
    """

    min: _TotalComparable
    max: _TotalComparable
    step: _TotalComparable | None = None

    class Config:
        arbitrary_types_allowed = True

    @validator('max')
    def _max_greater_min(cls, max: _TotalComparable, values: dict):
        min = values['min']
        assert min <= max, f'Interval must be with: {min} <= {max}'
        return max

    @validator('step')
    def _step_is_multiple(cls, step: _TotalComparable | None, values: dict):
        if not step:
            return None
        min = values['min']
        max = values['max']
        assert min % step == 0, f'Interval must be with: {min} % {step} == 0'
        assert max % step == 0, f'Interval must be with: {max} % {step} == 0'
        return step

    def __repr__(self) -> str:
        return f'[{self.min}]->[{self.max}]' + (f'//{self.step}' if self.step else '')

    def get_borders(self):
        return (self.min, self.max)

    def __contains__(self, items: _TotalComparable | Iterable[_TotalComparable] | None):
        if items is None:
            return False

        if not isinstance(items, Iterable):
            items = [items]

        return all(
            self.min <= item <= self.max and (not self.step or item % self.step == 0)  # type: ignore
            for item in items
        )
