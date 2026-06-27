"""
Type checking aliases.

:author: Doug Skrypa
"""

from __future__ import annotations

import sys
from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence, Type, TypeAlias, TypeVar, Union

try:
    from typing import Self
except ImportError:  # added in 3.11
    Self = TypeVar('Self')  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    from enum import Enum
    from pathlib import Path

    from .commands import Command
    from .inputs import Choices, Range
    from .parameters import Parameter, ParamGroup
    from .parameters.base import ParamBase


Bool: TypeAlias = bool | Any
StrSeq: TypeAlias = Sequence[str]
Strs: TypeAlias = str | StrSeq
StrIter: TypeAlias = Iterable[str]
IStrs: TypeAlias = str | StrIter
OptStr: TypeAlias = str | None
OptStrs: TypeAlias = Strs | None
Strings: TypeAlias = Collection[str]
PathLike: TypeAlias = Union[str, 'Path']

CommandObj = TypeVar('CommandObj', bound='Command')
CommandCls: TypeAlias = Type[CommandObj]
CommandAny: TypeAlias = CommandCls | CommandObj

AnyParam: TypeAlias = 'Parameter[Any, Any]'
ParamOrGroup: TypeAlias = Union['Parameter', 'ParamGroup', 'ParamBase']


if sys.version_info >= (3, 13):
    T = TypeVar('T', default=str, bound=Any)
    D = TypeVar('D', default=None, bound=Any)
    B = TypeVar('B', default=bool, bound=Any)
else:
    T = TypeVar('T', bound=Any)
    D = TypeVar('D', bound=Any)
    B = TypeVar('B', bound=Any)

E = TypeVar('E', bound='Enum')

TypeFunc: TypeAlias = Callable[[str], T]
ChoicesType: TypeAlias = Collection[T] | None
InputTypeFunc: TypeAlias = Union[TypeFunc[T], None]
NormalizedType: TypeAlias = Union[TypeFunc[T], 'Choices[T]', 'Range[T]', None]
