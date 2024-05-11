"""
Helpers for handling ``nargs=...`` for Parameters.

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import Any, Collection, FrozenSet, Iterable, Optional, Sequence, Set, Tuple, Union

__all__ = ['Nargs', 'NargsValue', 'REMAINDER', 'nargs_min_and_max_sums']

REMAINDER = type('REMAINDER', (), {})()
_UNBOUND = (None, REMAINDER)
NARGS_STR_RANGES = {'?': (0, 1), '*': (0, None), '+': (1, None), 'REMAINDER': (0, REMAINDER)}
SET_ERROR_FMT = 'Invalid nargs={!r} set - expected non-empty set where all values are integers >= 0'
SEQ_ERROR_FMT = 'Invalid nargs={!r} sequence - expected 2 ints where 0 <= a <= b or b is None'

NargsValue = Union[str, int, Tuple[int, Optional[int]], Sequence[int], Set[int], FrozenSet[int], range, type(REMAINDER)]


class Nargs:
    """
    Helper class for validating the number of values provided for a given :class:`.Parameter`.  Unifies the
    handling of different ways of specifying the required number of values.

    Acceptable values include ``?``, ``*``, and ``+``, and they have the same meaning that they have in argparse.
    Additionally, integers, a range of integers, or a set/tuple of integers are accepted for more specific requirements.
    """

    __slots__ = ('_orig', 'range', 'min', 'max', 'allowed', 'variable', '_has_upper_bound')
    _orig: NargsValue
    range: Optional[range]
    min: Optional[int]
    max: Optional[int]
    allowed: Collection[int]
    variable: bool

    def __init__(self, nargs: NargsValue):  # pylint: disable=R0912
        self._orig = nargs
        self.range = None
        if isinstance(nargs, int):
            if nargs < 0:
                raise ValueError(f'Invalid {nargs=} integer - must be >= 0')
            self.min = self.max = nargs
            self.allowed = (nargs,)
        elif isinstance(nargs, str):
            try:
                self.min, self.max = self.allowed = NARGS_STR_RANGES[nargs]
            except KeyError as e:
                raise ValueError(f'Invalid {nargs=} string - expected one of ?, *, or +') from e
        elif isinstance(nargs, range):
            if not 0 <= nargs.start < nargs.stop or nargs.step < 0:
                raise ValueError(f'Invalid {nargs=} range - expected positive step and 0 <= start < stop')
            self.range = nargs
            self.allowed = nargs
            self.min = nargs.start
            # As long as range.start < range.stop and range.step > 0, it will yield at least 1 value
            self.max = next(reversed(nargs))  # simpler than calculating, especially for step!=1
        elif isinstance(nargs, set):
            if not nargs:
                raise ValueError(SET_ERROR_FMT.format(nargs))
            elif not all(isinstance(v, int) for v in nargs):
                raise TypeError(SET_ERROR_FMT.format(nargs))

            self.allowed = self._orig = frozenset(nargs)  # Prevent modification after init
            self.min = min(nargs)
            if self.min < 0:
                raise ValueError(SET_ERROR_FMT.format(nargs))
            self.max = max(nargs)
        elif isinstance(nargs, Sequence):
            try:
                self.min, self.max = self.allowed = a, b = nargs
            except (ValueError, TypeError) as e:
                raise e.__class__(SEQ_ERROR_FMT.format(nargs)) from e

            if not (isinstance(a, int) and (b in _UNBOUND or isinstance(b, int))):
                raise TypeError(SEQ_ERROR_FMT.format(nargs))
            elif 0 > a or (b not in _UNBOUND and a > b):
                raise ValueError(SEQ_ERROR_FMT.format(nargs))
        elif nargs is REMAINDER:
            self.min, self.max = self.allowed = (0, REMAINDER)
        else:
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
            return f'{self.min} or more' if self.max is None else self.max.__class__.__name__
        elif self.min == self.max:
            return str(self.min)
        elif isinstance(self.allowed, frozenset):
            return f'{{{",".join(map(str, sorted(self.allowed)))}}}'
        else:
            return f'{self.min} ~ {self.max}'

    def __contains__(self, num: int) -> bool:
        """See :meth:`.satisfied`"""
        return self.satisfied(num)

    def __eq__(self, other: Union[Nargs, int]) -> bool:
        if isinstance(other, Nargs):
            return self._eq_nargs(other)
        elif isinstance(other, int):
            return self.min == self.max == other
        else:
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
        allowed = self.allowed
        if other.range is not None:
            try_all = other.min in allowed and other.max in allowed
            return try_all and all(v in allowed for v in other.range)  # less mem than large set(other.range)
        else:
            return allowed == set(other.allowed)

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
            return len(parsed_values) >= self.max
        return False

    @property
    def has_upper_bound(self) -> bool:
        return self._has_upper_bound

    @property
    def upper_bound(self) -> Union[int, float]:
        return self.max if self._has_upper_bound else float('inf')


def nargs_min_and_max_sums(nargs_objects: Iterable[Nargs]) -> tuple[int, Union[int, float]]:
    min_sum, max_sum = 0, 0
    iter_nargs = iter(nargs_objects)
    for obj in iter_nargs:
        min_sum += obj.min
        if obj._has_upper_bound:
            max_sum += obj.max
        else:
            max_sum = float('inf')
            break

    for obj in iter_nargs:  # If any had no upper bound, then this loop will complete the min total
        min_sum += obj.min  # Otherwise, it will not have anything to iterate over

    return min_sum, max_sum
