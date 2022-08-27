"""
Utilities for extracting types from annotations, finding / storing program metadata, and other misc utilities.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from enum import Flag
from inspect import isclass
from shutil import get_terminal_size
from time import monotonic
from typing import Any, Union, Optional, TypeVar, get_type_hints, List

try:
    from typing import get_origin, get_args as _get_args  # pylint: disable=C0412
except ImportError:  # Added in 3.8; the versions from 3.8 are copied here
    from .compat import get_origin, _get_args

try:
    from types import NoneType
except ImportError:  # Added in 3.10
    NoneType = type(None)

from .compat import decompose_flag, missing_flag

Bool = Union[bool, Any]
FlagEnum = TypeVar('FlagEnum', bound='FixedFlag')
_NotSet = object()


def camel_to_snake_case(text: str, delim: str = '_') -> str:
    return ''.join(f'{delim}{c}' if i and c.isupper() else c for i, c in enumerate(text)).lower()


# region Annotation Inspection


def get_descriptor_value_type(command_cls: type, attr: str) -> Optional[type]:
    try:
        annotation = get_type_hints(command_cls)[attr]
    except KeyError:
        return None

    return get_annotation_value_type(annotation)


def get_annotation_value_type(annotation) -> Optional[type]:
    origin = get_origin(annotation)
    # Note on get_origin return values:
    # get_origin(List[str]) -> list
    # get_origin(List) -> list
    # get_origin(list[str]) -> list
    # get_origin(list) -> None
    if origin is None and isinstance(annotation, type):
        return annotation
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, annotation)
    elif origin is Union:
        return _type_from_union(annotation)
    return None


def get_args(annotation) -> tuple:
    """
    Wrapper around :func:`python:typing.get_args` for 3.7~8 compatibility, to make it behave more like it does in 3.9+
    """
    if getattr(annotation, '_special', False):  # 3.7-3.8 generic collection alias with no content types
        return ()
    return _get_args(annotation)


def _type_from_union(annotation) -> Optional[type]:
    args = get_args(annotation)
    # Note: Unions of a single argument return the argument; i.e., Union[T] returns T, so the len can never be 1
    if len(args) == 2 and NoneType in args:
        arg = args[0] if args[1] is NoneType else args[1]
    else:
        return None

    origin = get_origin(arg)
    if origin is None and isinstance(arg, type):
        return arg
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, arg)
    else:
        return None


def _type_from_collection(origin, annotation) -> Optional[type]:
    args = get_args(annotation)
    try:
        annotation = args[0]
    except IndexError:  # The annotation was a collection with no content types specified
        return origin

    n_args = len(args)
    if n_args > 2 or (n_args > 1 and (origin is not tuple or args[1] is not Ellipsis)):
        return None

    origin = get_origin(annotation)
    if origin is None and isinstance(annotation, type):
        return annotation
    elif origin is Union:
        return _type_from_union(annotation)
    else:
        return None


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


class FixedFlag(Flag):
    """Extends Flag to work around breaking changes in 3.11 for repr, missing, and pseudo-members."""

    def __repr__(self) -> str:
        # In 3.11, this needs to be declared in the parent of a Flag that actually has members - it breaks if it is
        # defined in a mixin or the class with members.
        names = '|'.join(part._name_ for part in self._decompose())
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

        return missing_flag(cls, value)

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
        return decompose_flag(self.__class__, self._value_, self._name_)[0]

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
