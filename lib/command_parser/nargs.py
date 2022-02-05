"""
:author: Doug Skrypa
"""

from typing import Union

NargsValue = Union[str, int, tuple[int, int], range]

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
        elif isinstance(nargs, tuple):
            if len(nargs) != 2 or not all(isinstance(v, int) for v in nargs) or not 0 <= nargs[0] <= nargs[1]:
                raise ValueError(f'Invalid {nargs=} tuple - expected 2-tuple of integers where 0 <= a <= b')
            self.min, self.max = self.allowed = nargs
        elif isinstance(nargs, range):
            if not 0 <= nargs.start <= nargs.stop or nargs.step < 0:
                raise ValueError(f'Invalid {nargs=} range - expected positive step and 0 <= start <= stop')
            self.range = nargs
            self.allowed = nargs
            self.min = nargs.start
            self.max = nargs.stop

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
        else:
            return f'{self.min} or {self.max}'

    def __contains__(self, num: int) -> bool:
        return self.satisfied(num)

    def __eq__(self, other: Union['Nargs', int]) -> bool:
        if isinstance(other, Nargs):
            return self.allowed == other.allowed
        elif isinstance(other, int):
            return self.min == self.max == other
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._orig)

    def satisfied(self, count: int) -> bool:
        if self.max is None:
            return count >= self.min
        else:
            return count in self.allowed

    def needs_more(self, count: int) -> bool:
        return count < self.min

    def allows_more(self, count: int) -> bool:
        return self.max is None or count < self.max
