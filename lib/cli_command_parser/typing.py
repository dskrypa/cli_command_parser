"""
Type checking aliases.

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Pattern,
    Sequence,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from datetime import date, datetime, time, timedelta
    from enum import Enum
    from pathlib import Path

    from .commands import Command
    from .config import AllowLeadingDash, CommandConfig
    from .core import CommandMeta
    from .inputs import InputType
    from .parameters import Parameter, ParamGroup

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
TypeFunc = Callable[[str], T_co]

NT = TypeVar('NT', bound=float, covariant=True)
Number = Union[NT, None]
NumType = Callable[[Union[str, float, int]], NT]
RngType = Union[range, int, Sequence[int]]

InputTypeFunc = Union[None, TypeFunc, 'InputType', range, Type['Enum'], Pattern]
ChoicesType = Union[Collection[Any], None]

Bool = Union[bool, Any]
StrSeq = Sequence[str]
Strs = Union[str, StrSeq]
StrIter = Iterable[str]
IStrs = Union[str, StrIter]
OptStr = Union[str, None]
OptStrs = Union[Strs, None]
Strings = Collection[str]
PathLike = Union[str, 'Path']

Locale = Union[str, Tuple[Union[str, None], Union[str, None]]]
TimeBound = Union['datetime', 'date', 'time', 'timedelta', None]

FP = Union[TextIO, BinaryIO]
Deserializer = Callable[[Union[str, bytes, FP]], Any]
Serializer = Callable[..., Union[str, bytes, None]]
Converter = Union[Deserializer, Serializer]

Config = Union['CommandConfig', None]
AnyConfig = Union[Config, Dict[str, Any]]
LeadingDash = Union['AllowLeadingDash', str, bool]

Param = TypeVar('Param', bound='Parameter')
ParamList = List[Param]
ParamOrGroup = Union[Param, 'ParamGroup']

CommandObj = TypeVar('CommandObj', bound='Command')
CommandType = TypeVar('CommandType', bound='CommandMeta')
CommandCls = Union[CommandType, Type[CommandObj]]
CommandAny = Union[CommandCls, CommandObj]

CommandMethod = Callable[[CommandObj], T_co]
DefaultFunc = Union[Callable[[], T_co], CommandMethod]
