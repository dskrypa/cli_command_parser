"""
Type checking aliases.

:author: Doug Skrypa
"""

from __future__ import annotations

import sys
from collections.abc import Collection
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Pattern,
    Protocol,
    Sequence,
    Type,
    TypeAlias,
    TypeVar,
    Union,
)

try:
    from typing import Self
except ImportError:  # added in 3.11
    Self = TypeVar('Self')  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    from pathlib import Path

    from .commands import Command
    from .inputs import InputType, Regex
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

ParamOrGroup: TypeAlias = Union['Parameter', 'ParamGroup', 'ParamBase']


if sys.version_info >= (3, 13):
    T = TypeVar('T', default=str, covariant=True, bound=Any)
    D = TypeVar('D', default=None, covariant=True, bound=Any)
    B = TypeVar('B', default=bool, covariant=True, bound=Any)
else:
    T = TypeVar('T', covariant=True, bound=Any)
    D = TypeVar('D', covariant=True, bound=Any)
    B = TypeVar('B', covariant=True, bound=Any)


class TypeFunc(Protocol[T]):
    def __call__(self, value: str, /) -> T:
        pass


ChoicesType: TypeAlias = Collection[T] | None
InputTypeFunc: TypeAlias = Union[Type[T], TypeFunc[T], 'InputType[T]', range, Pattern, None]
NormalizedType: TypeAlias = Union[Type[T], TypeFunc[T], 'InputType[T]', 'Regex[str]', None]
