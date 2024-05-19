"""
Custom numeric input handlers for Parameters

:author: Doug Skrypa
"""
# pylint: disable=W0622

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from ..typing import NT, Bool, Number, NumType, RngType
from .base import InputType
from .exceptions import InputValidationError
from .utils import RangeMixin, range_str

__all__ = ['Range', 'NumRange']

_range = range


class NumericInput(InputType[NT], ABC):
    __slots__ = ()
    type: NumType

    def is_valid_type(self, value: str) -> bool:
        """
        Called during parsing when :meth:`.Parameter.would_accept` is called to determine if the value would be
        accepted later for processing / conversion when called.

        :param value: The parsed argument to validate
        :return: True if this input would accept it for processing later (where it may still be rejected), False if
          it should be rejected before attempting to process / convert / store it.
        """
        try:
            self.type(value)
        except (ValueError, TypeError):
            return False
        return True

    @abstractmethod
    def _range_str(self, var: str = 'N') -> str:
        raise NotImplementedError

    def format_metavar(self, choice_delim: str = ',', sort_choices: bool = False) -> str:
        return f'{{{self._range_str()}}}'

    def fix_default(self, value: Union[str, NT, None]) -> Optional[NT]:
        if value is None or not isinstance(value, str) or not self._fix_default:
            return value
        return self(value)


class Range(NumericInput[NT]):
    """
    A range of integers that uses the builtin :class:`python:range`.  If a range object is passed to a
    :class:`.Parameter` as the ``type=`` value, it will automatically be wrapped by this class.

    :param range: A :class:`python:range` object
    :param snap: If True and a provided value is outside the allowed range, snap to the nearest bound.  The min or max
      of the provided range (not necessarily the start/stop values) will be used, depending on which one the provided
      value is closer to.
    :param type: Callable that returns a numeric type, to be used on parsed values before validating whether they are
      in the allowed range.  Defaults to :class:`python:int`.
    :param fix_default: Whether default values should be normalized using :meth:`~NumericInput.fix_default`.
    """

    type: NumType = int
    range: Optional[_range]
    snap: bool

    def __init__(self, range: RngType, snap: Bool = False, type: NumType = None, fix_default: Bool = True):  # noqa
        super().__init__(fix_default)
        self.snap = snap
        if isinstance(range, int):
            self.range = _range(range)
        elif not isinstance(range, _range):
            self.range = _range(*range)
        else:
            self.range = range
        if type is not None:
            self.type = type

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.range!r}, snap={self.snap!r}, type={self.type!r})>'

    def _range_str(self, var: str = 'N') -> str:
        rng_min, rng_max = min(self.range), max(self.range)
        step = abs(self.range.step)
        base = f'{rng_min} <= {var} <= {rng_max}'
        return base if step == 1 else f'{base}, {step=}'

    def __call__(self, value: str) -> NT:
        value = self.type(value)
        if value in self.range:
            return value
        elif self.snap:
            if (rng_min := min(self.range)) > value:
                return rng_min
            return max(self.range)

        raise InputValidationError(f'expected a value in the range {self._range_str()}')


class NumRange(RangeMixin, NumericInput[NT]):
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
    :param fix_default: Whether default values should be normalized using :meth:`~NumericInput.fix_default`.
    """

    __slots__ = ('type', 'snap', 'min', 'max', 'include_min', 'include_max')
    snap: bool

    def __init__(
        self,
        type: NumType = None,  # noqa
        snap: Bool = False,
        *,
        min: Number = None,  # noqa
        max: Number = None,  # noqa
        include_min: Bool = True,
        include_max: Bool = False,
        fix_default: Bool = True,
    ):
        if min is None and max is None:
            raise ValueError('NumRange inputs must be initialized with at least one of min and/or max values')
        elif min is not None and max is not None and min >= max:
            raise ValueError(f'Invalid {min=} >= {max=} - min must be less than max')

        super().__init__(fix_default)
        if type is None:
            self.type = float if isinstance(min, float) or isinstance(max, float) else int
        else:
            self.type = type

        if snap:
            if self.type is float:
                raise TypeError('Unable to snap to extrema with type=float')
            real_min = min if include_min else min + 1
            real_max = max if include_max else max - 1
            if real_min >= real_max:
                raise ValueError(
                    f'Invalid {min=} >= {max=} with snap=True, {include_min=},'
                    f' {include_max=} - snap would produce invalid values'
                )

        self.snap = snap
        self.min = self.type(min) if min is not None else min  # for floats especially, such as a range like 0~1, this
        self.max = self.type(max) if max is not None else max  # helps to highlight the type in reprs
        self.include_min = include_min
        self.include_max = include_max

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.type!r}, snap={self.snap!r})[{self._range_str()}]>'

    def _range_str(self, var: str = 'N') -> str:
        return range_str(self.min, self.max, self.include_min, self.include_max, var)

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
        raise InputValidationError(f'expected a value in the range {self._range_str()}')

    def __call__(self, value: str) -> NT:
        value = self.type(value)
        if self.value_lt_min(value):
            return self.handle_invalid(self.min, self.include_min, 1)
        elif self.value_gt_max(value):
            return self.handle_invalid(self.max, self.include_max, -1)
        else:
            return value
