"""
:author: Doug Skrypa
"""

from typing import Union, Optional, Sequence, Tuple, Set

NargsValue = Union[str, int, Tuple[int, Optional[int]], Sequence[int], Set[int], range]

NARGS_STR_RANGES = {'?': (0, 1), '*': (0, None), '+': (1, None)}
SET_ERROR_FMT = 'Invalid nargs={!r} set - expected non-empty set where all values are integers >= 0'
SEQ_ERROR_FMT = 'Invalid nargs={!r} sequence - expected 2 ints where 0 <= a <= b or b is None'


class Nargs:
    """
    Helper class for validating the number of values provided for a given :class:`~.parameters.Parameter`.  Unifies the
    handling of different ways of specifying the required number of values.

    Acceptable values include ``?``, ``*``, and ``+``, and they have the same meaning that they have in argparse.
    Additionally, integers, a range of integers, or a set/tuple of integers are accepted for more specific requirements.
    """

    def __init__(self, nargs: NargsValue):
        self._orig = nargs
        self.range = None
        if isinstance(nargs, int):
            if nargs < 0:
                raise ValueError(f'Invalid nargs={nargs!r} integer - must be >= 0')
            self.min = self.max = nargs
            self.allowed = (nargs,)
        elif isinstance(nargs, str):
            try:
                self.min, self.max = self.allowed = NARGS_STR_RANGES[nargs]
            except KeyError as e:
                raise ValueError(f'Invalid nargs={nargs!r} string - expected one of ?, *, or +') from e
        elif isinstance(nargs, range):
            if not 0 <= nargs.start < nargs.stop or nargs.step < 0:
                raise ValueError(f'Invalid nargs={nargs!r} range - expected positive step and 0 <= start < stop')
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

            if not (isinstance(a, int) and (b is None or isinstance(b, int))):
                raise TypeError(SEQ_ERROR_FMT.format(nargs))
            elif 0 > a or (b is not None and a > b):
                raise ValueError(SEQ_ERROR_FMT.format(nargs))
        else:
            raise TypeError(f'Unexpected type={nargs.__class__.__name__} for nargs={nargs!r}')

        self.variable = self.min != self.max

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._orig!r})'

    def __str__(self) -> str:
        rng = self.range
        if rng is not None:
            return f'{rng.start} ~ {rng.stop}' if rng.step == 1 else f'{rng.start} ~ {rng.stop} (step={rng.step})'
        elif self.max is None:
            return f'{self.min} or more'
        elif self.min == self.max:
            return str(self.min)
        elif isinstance(self.allowed, frozenset):
            return '{{{}}}'.format(','.join(map(str, sorted(self.allowed))))
        else:
            return f'{self.min} ~ {self.max}'

    def __contains__(self, num: int) -> bool:
        """See :meth:`.satisfied`"""
        return self.satisfied(num)

    def __eq__(self, other: Union['Nargs', int]) -> bool:
        if isinstance(other, Nargs):
            if self.max is None:
                return other.max is None and self.min == other.min
            elif other.max is None:
                return False
            elif isinstance(other._orig, type(self._orig)):
                return self.allowed == other.allowed
            # After this point, the allowed / range attribute types cannot match because the originals did not match
            elif isinstance(self.allowed, frozenset):
                return self._compare_allowed_set(other)
            elif isinstance(other.allowed, frozenset):
                return other._compare_allowed_set(self)
            rng = self.range or other.range
            if rng:
                return self.min == other.min and self.max == other.max and rng.step == 1
            else:
                return self.min == other.min and self.max == other.max
        elif isinstance(other, int):
            return self.min == self.max == other
        else:
            return NotImplemented

    def _compare_allowed_set(self, other: 'Nargs') -> bool:
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
        if self.max is None:
            return count >= self.min
        else:
            return count in self.allowed
