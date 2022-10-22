from __future__ import annotations

from typing import Generic, Iterable

from core.utils.types import _TCT
from pydantic import validator
from pydantic.generics import GenericModel


class Interval(GenericModel, Generic[_TCT]):
    """
    Interval represents value range (both `[min, max]` inclusevly).
    If `step` is provided, it should be a multiplier for `min` and `max`.
    """

    min: _TCT
    max: _TCT
    step: _TCT | None = None

    class Config:
        arbitrary_types_allowed = True

    @validator('max')
    def _max_greater_min(cls, max: _TCT, values: dict):
        min = values['min']
        assert min <= max, f'Interval must be with: {min} <= {max}'
        return max

    @validator('step')
    def _step_is_multiple(cls, step: _TCT | None, values: dict):
        if not step:
            return None
        try:
            min = values['min']
            max = values['max']
        except KeyError as e:
            raise ValueError(f'Both min and max are required: {e}')


        assert min % step == 0, f'Interval must be with: {min} % {step} == 0'
        assert max % step == 0, f'Interval must be with: {max} % {step} == 0'
        return step

    def __repr__(self) -> str:
        return f'[{self.min}]->[{self.max}]' + (f'//{self.step}' if self.step else '')

    @property
    def borders(self):
        return (self.min, self.max)

    def __contains__(self, items: _TCT | Iterable[_TCT] | None):
        if items is None:
            return False

        if not isinstance(items, Iterable):
            items = [items]

        return all(
            self.min <= item <= self.max and (not self.step or item % self.step == 0)  # type: ignore
            for item in items
        )

