"""
Custom numeric input handlers for Parameters

:author: Doug Skrypa
"""
# pylint: disable=W0622

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from operator import le, lt, ge, gt
from typing import TYPE_CHECKING, Union, Callable, Optional

from .base import InputType

if TYPE_CHECKING:
    from ..utils import Bool

__all__ = ['Range', 'NumRange']

Number = Union[int, float, None]
NumType = Callable[[str], Union[int, float]]


class NumericInput(InputType, ABC):
    type: NumType

    def is_valid_type(self, value: str) -> bool:
        try:
            self.type(value)
        except (ValueError, TypeError):
            return False
        return True

    @abstractmethod
    def _range_str(self, var: str = 'N') -> str:
        raise NotImplementedError

    def format_metavar(self, choice_delim: str = ',') -> str:
        return f'{{{self._range_str()}}}'


class Range(NumericInput):
    """
    A range of integers that uses the builtin :class:`python:range`.  If a range object is passed to a
    :class:`.Parameter` as the ``type=`` value, it will automatically be wrapped by this class.

    :param range: A :class:`python:range` object
    :param snap: If True and a provided value is outside the allowed range, snap to the nearest bound.  The min or max
      of the provided range (not necessarily the start/stop values) will be used, depending on which one the provided
      value is closer to.
    """

    type: NumType = int
    range: Optional[builtins.range]
    snap: bool

    def __init__(self, range: builtins.range, snap: Bool = False, type: NumType = None):  # noqa
        self.snap = snap
        self.range = range
        if type is not None:
            self.type = type

    def _range_str(self, var: str = 'N') -> str:
        rng_min, rng_max = min(self.range), max(self.range)
        step = abs(self.range.step)
        base = f'{rng_min} <= {var} <= {rng_max}'
        return base if step == 1 else f'{base}, step={step}'

    def __call__(self, value: str) -> Union[float, int]:
        value = self.type(value)
        if value in self.range:
            return value
        elif self.snap:
            rng_min = min(self.range)
            if value < rng_min:
                return rng_min
            return max(self.range)

        raise ValueError(f'expected a value in the range {self._range_str()}')


class NumRange(NumericInput):
    """
    A range of integers or floats, optionally only bounded on one side.

    By default, the min and max behave like the builtin :class:`python:range` - the min is inclusive, and the max
    is exclusive.

    :param type: The type for values, or any callable that returns an int/float
    :param snap: If True and a provided value is outside the allowed range, snap to the nearest bound.  Respects
      inclusivity/exclusivity of the bound.  Not supported for floats since there is not an obviously correct
      behavior for handling them in this context.
    :param min: The minimum allowed value, or None to have no lower bound
    :param max: The maximum allowed value, or None to have no upper bound
    :param include_min: Whether the minimum is inclusive (default: True)
    :param include_max: Whether the maximum is inclusive (default: False)
    """

    snap: bool
    min: Number
    max: Number
    include_min: bool
    include_max: bool

    def __init__(
        self,
        type: NumType = None,  # noqa
        snap: Bool = False,
        *,
        min: Number = None,  # noqa
        max: Number = None,  # noqa
        include_min: Bool = True,
        include_max: Bool = False,
    ):
        if min is None and max is None:
            raise ValueError('NumRange inputs must be initialized with at least one of min and/or max values')
        elif min is not None and max is not None and min >= max:
            raise ValueError(f'Invalid min={min} >= max={max} - min must be less than max')

        if type is None:
            self.type = float if float in (builtins.type(min), builtins.type(max)) else int
        else:
            self.type = type

        if snap:
            if self.type is float:
                raise TypeError('Unable to snap to extrema with type=float')
            real_min = min if include_min else min + 1
            real_max = max if include_max else max - 1
            if real_min >= real_max:
                raise ValueError(
                    f'Invalid min={min} >= max={max} with snap=True, include_min={include_min},'
                    f' include_max={include_max} - snap would produce invalid values'
                )

        self.snap = snap
        self.min = min
        self.max = max
        self.include_min = include_min
        self.include_max = include_max

    def _range_str(self, var: str = 'N') -> str:
        if self.min is not None:
            min_str = '{} {} '.format(self.min, '<=' if self.include_min else '<')
        else:
            min_str = ''

        if self.max is not None:
            max_str = ' {} {}'.format('<=' if self.include_max else '<', self.max)
        else:
            max_str = ''

        return f'{min_str}{var}{max_str}'

    def handle_invalid(self, bound: Number, inclusive: bool, snap_dir: int) -> Number:
        """
        Handle calculating / returning a snap value or raise an exception if snapping to the bound is not allowed.

        May be overridden in a subclass to support snapping for float values or other behavior.

        :param bound: The bound (min or max) that was violated
        :param inclusive: True if the bound is inclusive, False if it is exclusive
        :param snap_dir: The direction to adjust the bound if it is exclusive as ``+1`` or ``-1``
        :return: The snap value if :attr:`.snap` is True, otherwise a :class:`python:ValueError` is raised
        """
        if self.snap:
            return bound if inclusive else (bound + snap_dir)
        raise ValueError(f'expected a value in the range {self._range_str()}')

    def __call__(self, value: str) -> Union[float, int]:
        value = self.type(value)
        if self.min is not None:
            below_min = lt if self.include_min else le  # Bad if < when inclusive, bad if <= when exclusive
            if below_min(value, self.min):
                return self.handle_invalid(self.min, self.include_min, 1)
        if self.max is not None:
            above_max = gt if self.include_max else ge
            if above_max(value, self.max):
                return self.handle_invalid(self.max, self.include_max, -1)
        return value
