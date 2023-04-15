"""
Utilities for working with terminals, strings, and Enums.

:author: Doug Skrypa
"""

from __future__ import annotations

from enum import Flag, EnumMeta
from shutil import get_terminal_size
from time import monotonic
from typing import Any, Callable, TypeVar, List

try:
    from enum import CONFORM
except ImportError:
    CONFORM = None

FlagEnum = TypeVar('FlagEnum', bound='FixedFlag')
_NotSet = object()

# region Text Processing / Formatting


def camel_to_snake_case(text: str, delim: str = '_') -> str:
    return ''.join(f'{delim}{c}' if i and c.isupper() else c for i, c in enumerate(text)).lower()


def short_repr(obj: Any, max_len: int = 100, sep: str = '...', func: Callable[[Any], str] = repr) -> str:
    obj_repr = func(obj)
    if len(obj_repr) > max_len:
        part_len = (max_len - len(sep)) // 2
        return f'{obj_repr[:part_len]}{sep}{obj_repr[-part_len:]}'
    return obj_repr


def _parse_tree_target_repr(target) -> str:
    try:
        return target.__name__
    except AttributeError:
        return repr(target)


# endregion


class MissingMixin:
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper()]  # noqa
            except KeyError:
                pass
        return super()._missing_(value)  # noqa


class FixedFlagMeta(EnumMeta):
    """
    This metaclass is only used to maintain the same behavior for Flag pseudo-members between 3.7-3.10 and 3.11 when
    the behavior was parameterized via the ``boundary`` parameter.
    """

    def __new__(mcs, *args, **kwargs):
        if CONFORM:
            kwargs['boundary'] = CONFORM
        return super().__new__(mcs, *args, **kwargs)


class FixedFlag(Flag, metaclass=FixedFlagMeta):
    """Extends Flag to work around breaking changes in 3.11 for repr, missing, and pseudo-members."""

    def __repr__(self) -> str:
        # In 3.11, this needs to be declared in the parent of a Flag that actually has members - it breaks if it is
        # defined in a mixin or the class with members.
        names = '|'.join(part._name_ for part in self._decompose())  # noqa
        return f'<{self.__class__.__name__}:{names}>'

    @classmethod
    def _missing_(cls, value) -> FlagEnum:
        if isinstance(value, str):
            if value.startswith(('!', '~')):
                invert = True
                value = value[1:]
            else:
                invert = False

            try:
                member = cls._missing_str(value)
            except KeyError:
                expected = ', '.join(cls._member_map_)
                raise ValueError(f'Invalid {cls.__name__} value={value!r} - expected one of {expected}') from None
            else:
                return ~member if invert else member  # pylint: disable=E1130
        elif not isinstance(value, int):
            raise TypeError(f'Unexpected type={value.__class__.__name__} for a {cls.__name__}')

        return super()._missing_(value)

    @classmethod
    def _missing_str(cls, value: str) -> FlagEnum:
        try:
            return cls._member_map_[value.upper()]  # noqa
        except KeyError:
            pass
        if '|' in value:
            tmp = cls(0)
            for part in map(str.strip, value.split('|')):
                if not part:
                    continue
                try:
                    tmp |= cls._member_map_[part.upper()]
                except KeyError:
                    break
            else:
                if tmp._value_ != 0:
                    return tmp

        raise KeyError

    def _decompose(self) -> List[FlagEnum]:
        if self._name_ is None or '|' in self._name_:  # | check is for 3.11 where pseudo-members are assigned names
            val = self._value_
            members = ((mem, mem._value_) for mem in self.__class__)
            return sorted(mem for mem, mem_val in members if mem_val & val == mem_val)  # noqa
        return [self]

    def __lt__(self, other: FlagEnum) -> bool:
        return self._value_ < other._value_


class Terminal:  # pylint: disable=R0903
    __slots__ = ('_cache_time', '_last_time', '_width')

    def __init__(self, cache_time: float = 1):
        self._cache_time = cache_time
        self._last_time = 0
        self._width = 80

    @property
    def width(self) -> int:
        if monotonic() - self._last_time > self._cache_time:
            self._width = get_terminal_size()[0]
            self._last_time = monotonic()
        return self._width
