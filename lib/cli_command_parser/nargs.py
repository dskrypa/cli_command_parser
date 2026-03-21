"""
Helpers for handling ``nargs=...`` for Parameters.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any, Collection, FrozenSet, Literal, TypeAlias

__all__ = ['Nargs', 'NargsValue', 'REMAINDER']


class _Remainder(Enum):
    """Provides the sentinel value for REMAINDER in a way that is fully compatible with type checkers."""

    REMAINDER = 'REMAINDER'

    def __str__(self) -> str:
        return self.name


REMAINDER = _Remainder.REMAINDER
_UNBOUND = (None, REMAINDER)
_Max: TypeAlias = int | None | _Remainder
NARGS_STR_RANGES = {'?': (0, 1), '*': (0, None), '+': (1, None), 'REMAINDER': (0, REMAINDER)}
SET_ERROR_FMT = 'Invalid nargs={!r} set - expected non-empty set where all values are integers >= 0'
SEQ_ERROR_FMT = 'Invalid nargs={!r} sequence - expected 2 ints where 0 <= a <= b or b is None'

NargsStr = Literal['?', '*', '+', 'REMAINDER']
NargsValue: TypeAlias = (
    NargsStr | int | tuple[int, _Max] | Sequence[int] | set[int] | FrozenSet[int] | range | _Remainder
)


class Nargs:
    """
    Helper class for validating the number of values provided for a given :class:`.Parameter`.  Unifies the
    handling of different ways of specifying the required number of values.

    Acceptable values include ``?``, ``*``, and ``+``, and they have the same meaning that they have in argparse.
    Additionally, integers, a range of integers, or a set/tuple of integers are accepted for more specific requirements.
    """

    # Note: most `type: ignore` comments are related to the use of _UNBOUND membership to determine that max is not
    # None or REMAINDER without explicit type verification via isinstance/similar.

    __slots__ = ('_orig', 'range', 'min', 'max', 'allowed', 'variable', '_has_upper_bound')
    _orig: NargsValue
    range: range | None
    min: int
    max: _Max
    allowed: Collection[int] | tuple[int, _Max]
    variable: bool

    def __init__(self, nargs: NargsValue):
        self._orig = nargs
        self.range = None

        match nargs:
            case int():
                if nargs < 0:
                    raise ValueError(f'Invalid {nargs=} integer - must be >= 0')
                self.min = self.max = nargs
                self.allowed = (nargs,)
            case str():
                try:
                    self.min, self.max = self.allowed = NARGS_STR_RANGES[nargs]
                except KeyError as e:
                    raise ValueError(f'Invalid {nargs=} string - expected one of ?, *, or +') from e
            case range():
                if not 0 <= nargs.start < nargs.stop or nargs.step < 0:
                    raise ValueError(f'Invalid {nargs=} range - expected positive step and 0 <= start < stop')
                self.range = nargs
                self.allowed = nargs
                self.min = nargs.start
                # As long as range.start < range.stop and range.step > 0, it will yield at least 1 value
                self.max = next(reversed(nargs))  # simpler than calculating, especially for step!=1
            case set():
                if not nargs:
                    raise ValueError(SET_ERROR_FMT.format(nargs))
                elif not all(isinstance(v, int) for v in nargs):
                    raise TypeError(SET_ERROR_FMT.format(nargs))

                self.allowed = self._orig = frozenset(nargs)  # Prevent modification after init
                self.min = min(nargs)
                if self.min < 0:
                    raise ValueError(SET_ERROR_FMT.format(nargs))
                self.max = max(nargs)
            case Sequence():
                try:
                    self.min, self.max = self.allowed = a, b = nargs  # type: ignore[misc,assignment]
                except (ValueError, TypeError) as e:
                    raise e.__class__(SEQ_ERROR_FMT.format(nargs)) from e

                if not (isinstance(a, int) and (b in _UNBOUND or isinstance(b, int))):
                    raise TypeError(SEQ_ERROR_FMT.format(nargs))
                elif 0 > a or (b not in _UNBOUND and a > b):  # type: ignore[operator]
                    raise ValueError(SEQ_ERROR_FMT.format(nargs))
            case _Remainder():
                self.min, self.max = self.allowed = (0, REMAINDER)
            case _:
                raise TypeError(f'Unexpected type={nargs.__class__.__name__} for {nargs=}')

        self.variable = self.min != self.max
        self._has_upper_bound = self.max not in _UNBOUND

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._orig!r})'

    def __str__(self) -> str:
        rng = self.range
        if rng is not None:
            return f'{rng.start} ~ {rng.stop}' if rng.step == 1 else f'{rng.start} ~ {rng.stop} (step={rng.step})'
        elif not self._has_upper_bound:
            return f'{self.min} or more' if self.max is None else str(self.max)  # str(self.max) is for REMAINDER
        elif self.min == self.max:
            return str(self.min)
        elif isinstance(self.allowed, frozenset):
            return f'{{{",".join(map(str, sorted(self.allowed)))}}}'
        else:
            return f'{self.min} ~ {self.max}'

    def __contains__(self, num: int) -> bool:
        """See :meth:`.satisfied`"""
        return self.satisfied(num)

    def __eq__(self, other) -> bool:
        match other:
            case Nargs():
                return self._eq_nargs(other)
            case int():
                return self.min == self.max == other
            case _:
                return NotImplemented

    def _eq_nargs(self, other: Nargs) -> bool:
        if not self._has_upper_bound:
            return other.max is self.max and self.min == other.min
        elif not other._has_upper_bound:
            return False
        elif isinstance(other._orig, type(self._orig)):
            return self.allowed == other.allowed

        # After this point, the allowed / range attribute types cannot match because the originals did not match
        if isinstance(self.allowed, frozenset):
            return self._compare_allowed_set(other)
        elif isinstance(other.allowed, frozenset):
            return other._compare_allowed_set(self)

        rng = self.range or other.range
        return self.min == other.min and self.max == other.max and (not rng or rng.step == 1)

    def _compare_allowed_set(self, other: Nargs) -> bool:
        """
        Used internally to determine whether 2 Nargs instances are equivalent when they were initialized with different
        types of arguments.
        """
        if other.range is not None:
            allowed = self.allowed
            try_all = other.min in allowed and other.max in allowed
            return try_all and all(v in allowed for v in other.range)  # less mem than large set(other.range)
        else:
            return self.allowed == set(other.allowed)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._orig)

    def satisfied(self, count: int) -> bool:
        """
        Returns True if the minimum number of values have been provided to satisfy the requirements, and if the number
        of values has not exceeded the maximum allowed.  Returns False if the count is below the minimum or above the
        maximum.

        For more advanced use cases, such as range or a set of counts, the count must also match one of the specific
        numbers provided for this to return True.
        """
        if self._has_upper_bound:
            return count in self.allowed
        else:
            return count >= self.min

    def max_reached(self, parsed_values: Collection[Any]) -> bool:
        """
        :param parsed_values: The value(s) parsed so far for a Parameter.
        :return: True if ``parsed_values`` has a length and that length meets or exceeds the maximum count allowed,
          False otherwise.
        """
        if self._has_upper_bound:
            return len(parsed_values) >= self.max  # type: ignore[operator]
        return False

    @property
    def has_upper_bound(self) -> bool:
        return self._has_upper_bound

    @property
    def upper_bound(self) -> int | float:
        return self.max if self._has_upper_bound else float('inf')  # type: ignore[return-value]
