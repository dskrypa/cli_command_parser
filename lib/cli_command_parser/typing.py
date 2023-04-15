"""
Type checking aliases.

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar, Type, Union, Optional, Collection, Sequence, TextIO, BinaryIO
from typing import Tuple, List, Dict

if TYPE_CHECKING:
    from datetime import datetime, date, time, timedelta
    from enum import Enum
    from pathlib import Path
    from .commands import Command
    from .config import CommandConfig, AllowLeadingDash
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

InputTypeFunc = Union[None, TypeFunc, 'InputType', range, Type['Enum']]
ChoicesType = Optional[Collection[Any]]

Bool = Union[bool, Any]
Strs = Union[str, Sequence[str]]
OptStr = Optional[str]
OptStrs = Optional[Strs]
Strings = Collection[str]
PathLike = Union[str, 'Path']

Locale = Union[str, Tuple[Optional[str], Optional[str]]]
TimeBound = Union['datetime', 'date', 'time', 'timedelta', None]

FP = Union[TextIO, BinaryIO]
Deserializer = Callable[[Union[str, bytes, FP]], Any]
Serializer = Callable[..., Union[str, bytes, None]]
Converter = Union[Deserializer, Serializer]

Config = Optional['CommandConfig']
AnyConfig = Union[Config, Dict[str, Any]]
LeadingDash = Union['AllowLeadingDash', str, bool]

Param = TypeVar('Param', bound='Parameter')
ParamList = List[Param]
ParamOrGroup = Union[Param, 'ParamGroup']

CommandObj = TypeVar('CommandObj', bound='Command')
CommandType = TypeVar('CommandType', bound='CommandMeta')
CommandCls = Union[CommandType, Type[CommandObj]]
CommandAny = Union[CommandCls, CommandObj]
