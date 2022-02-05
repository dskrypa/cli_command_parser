"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from functools import partial, update_wrapper
from types import MethodType
from typing import TYPE_CHECKING, Any, Union, Type, Sequence, Optional

if TYPE_CHECKING:
    from .parameters import Parameter

Bool = Union[bool, Any]
NargsValue = Union[str, int, tuple[int, int], range]

_NotSet = object()

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


class parameter_action:
    def __init__(self, method: MethodType):
        self.method = method
        update_wrapper(self, method)

    def __set_name__(self, parameter_cls: Type['Parameter'], name: str):
        """
        Registers the decorated method in the Parameter subclass's _actions dict, then replaces the action decorator
        with the original method.

        Since `__set_name__` is called on descriptors before their containing class's parent's `__init_subclass__` is
        called, name action/method name conflicts are handled by imitating a name mangled dunder attribute that will be
        unique to each subclass.  The mangled name is replaced with the friendlier `_actions` in
        :meth:`Parameter.__init_subclass__`.
        """
        try:
            actions = getattr(parameter_cls, f'_{parameter_cls.__name__}__actions')
        except AttributeError:
            actions = set()
            setattr(parameter_cls, f'_{parameter_cls.__name__}__actions', actions)

        actions.add(name)

    def __call__(self, *args, **kwargs) -> int:
        result = self.method(*args, **kwargs)
        return 1 if result is None else result

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return partial(self.__call__, instance)


class Args:
    def __init__(self, args: Optional[Sequence[str]]):
        self.raw = sys.argv[1:] if args is None else args
        self.remaining = self.raw
        self._parsed = {}
        self._provided = defaultdict(int)

    def __repr__(self) -> str:
        # return f'<{self.__class__.__name__}[raw={self.raw}]>'
        provided = dict(self._provided)
        return f'<{self.__class__.__name__}[parsed={self._parsed}, remaining={self.remaining}, {provided=}]>'

    def record_action(self, param: 'Parameter', val_count: int = 1):
        self._provided[param.name] += val_count

    def num_provided(self, param: 'Parameter') -> int:
        return self._provided[param.name]

    def __getitem__(self, param: 'Parameter'):
        try:
            return self._parsed[param.name]
        except KeyError:
            self._parsed[param.name] = value = param._init_value_factory()
            return value

    def __setitem__(self, param: 'Parameter', value):
        self._parsed[param.name] = value
