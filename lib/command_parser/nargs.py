"""
:author: Doug Skrypa
"""

from typing import Union, Sequence

NargsValue = Union[str, int, tuple[int, int], Sequence[int], set[int], range]

NARGS_STR_RANGES = {'?': (0, 1), '*': (0, None), '+': (1, None)}


class Nargs:
    def __init__(self, nargs: NargsValue):
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
                raise ValueError(f'Invalid {nargs=} set - expected non-empty set where all values are integers >= 0')
            elif not all(isinstance(v, int) for v in nargs):
                raise TypeError(f'Invalid {nargs=} set - expected non-empty set where all values are integers >= 0')
            self.allowed = self._orig = frozenset(nargs)  # Prevent modification after init
            self.min = min(nargs)
            if self.min < 0:
                raise ValueError(f'Invalid {nargs=} set - expected non-empty set where all values are integers >= 0')
            self.max = max(nargs)
        elif isinstance(nargs, Sequence):
            try:
                self.min, self.max = self.allowed = a, b = nargs
            except (ValueError, TypeError) as e:
                raise e.__class__(f'Invalid {nargs=} sequence - expected 2 ints where 0 <= a <= b or b is None') from e

            if not (isinstance(a, int) and (b is None or isinstance(b, int))):
                raise TypeError(f'Invalid {nargs=} sequence - expected 2 ints where 0 <= a <= b or b is None')
            elif 0 > a or (b is not None and a > b):
                raise ValueError(f'Invalid {nargs=} sequence - expected 2 ints where 0 <= a <= b or b is None')
        else:
            raise TypeError(f'Unexpected type={nargs.__class__.__name__} for {nargs=}')

        self.variable = self.min != self.max

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._orig!r})'

    def __str__(self) -> str:
        if (rng := self.range) is not None:
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
            elif rng := self.range or other.range:
                return self.min == other.min and self.max == other.max and rng.step == 1
            else:
                return self.min == other.min and self.max == other.max
        elif isinstance(other, int):
            return self.min == self.max == other
        else:
            return NotImplemented

    def _compare_allowed_set(self, other: 'Nargs') -> bool:
        allowed = self.allowed
        if other.range is not None:
            try_all = other.min in allowed and other.max in allowed
            return try_all and all(v in allowed for v in other.range)  # less mem than large set(other.range)
        else:
            return allowed == set(other.allowed)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._orig)

    def satisfied(self, count: int) -> bool:
        if self.max is None:
            return count >= self.min
        else:
            return count in self.allowed
