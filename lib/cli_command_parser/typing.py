"""
Type checking aliases.

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Iterable,
    Pattern,
    Sequence,
    Type,
    TypeAlias,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from datetime import date, datetime, time, timedelta
    from enum import Enum
    from numbers import Number as _Number
    from pathlib import Path

    from .commands import Command
    from .config import AllowLeadingDash, CommandConfig
    from .core import CommandMeta
    from .inputs import InputType
    from .parameters import Parameter, ParamGroup

T = TypeVar('T')
TypeFunc = Callable[[str], T]

NT = TypeVar('NT', bound='_Number')
Number: TypeAlias = NT | None
NumType = Callable[[Any], NT]
RngType = range | int | Sequence[int]

InputTypeFunc = Union[None, TypeFunc, 'InputType', range, Type['Enum'], Pattern]
ChoicesType = Collection[Any] | None

Bool = bool | Any
StrSeq = Sequence[str]
Strs = str | StrSeq
StrIter = Iterable[str]
IStrs = str | StrIter
OptStr = str | None
OptStrs = Strs | None
Strings = Collection[str]
PathLike = Union[str, 'Path']

Locale = str | tuple[OptStr, OptStr]
TimeBound = Union['datetime', 'date', 'time', 'timedelta', None]

Deserializer = Callable[[str | bytes | IO], Any]
Serializer = Callable[[Any, IO], None] | Callable[[Any], str | bytes]
Converter = Deserializer | Serializer

Config = Union['CommandConfig', None]
AnyConfig = Config | dict[str, Any]
LeadingDash = Union['AllowLeadingDash', str, bool]

Param = TypeVar('Param', bound='Parameter')
ParamList = list[Param]
ParamOrGroup = Union[Param, 'ParamGroup']

CommandObj = TypeVar('CommandObj', bound='Command')
CommandCls: TypeAlias = Type[CommandObj]
CommandAny: TypeAlias = CommandCls | CommandObj
