from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, AnyStr, BinaryIO, Callable, Literal, Protocol, TextIO, TypeAlias, TypeVar, Union

if TYPE_CHECKING:
    from datetime import date, datetime, time, timedelta
    from numbers import Number as _Number


Locale = str | tuple[str | None, str | None]
TimeBound: TypeAlias = Union['datetime', 'date', 'time', 'timedelta', None]

N = TypeVar('N', bound=Union['_Number', int, float])
Number: TypeAlias = N | None
NumType: TypeAlias = Callable[[str | Any], N]
RngType: TypeAlias = range | int | Sequence[int]

# There are many more compatible variations of file open modes, but enumerating every one results in poor readability
# of popup type hints.
OpenBinaryMode: TypeAlias = Literal['rb', 'wb']
OpenTextMode: TypeAlias = Literal['r', 'w']
OpenAnyMode: TypeAlias = str


# region Minimal IO Protocols

_T_co = TypeVar('_T_co', covariant=True)
_T_contra = TypeVar('_T_contra', contravariant=True)


class SupportsRead(Protocol[_T_co]):
    def read(self, length: int = ..., /) -> _T_co: ...


class SupportsReadLine(Protocol[_T_co]):
    def read(self, length: int = ..., /) -> _T_co: ...
    def readline(self) -> _T_co: ...


class SupportsWrite(Protocol[_T_contra]):
    def write(self, s: _T_contra, /) -> object: ...


class SupportsRW(Protocol[AnyStr]):
    def read(self, length: int = ..., /) -> AnyStr: ...
    def readline(self) -> AnyStr: ...
    def write(self, s: AnyStr, /) -> object: ...


# endregion


# region Serializer Protocols


class FileSerializer(Protocol[AnyStr]):
    __slots__ = ()

    def load(self, fp: SupportsRead[AnyStr] | SupportsReadLine[AnyStr]) -> Any: ...
    def dump(self, obj: Any, fp: SupportsWrite[AnyStr]) -> None: ...


class AnyStrSerializer(Protocol[AnyStr]):
    __slots__ = ()

    def loads(self, data: AnyStr) -> Any: ...
    def dumps(self, obj: Any) -> AnyStr: ...


class FullSerializer(FileSerializer[AnyStr], AnyStrSerializer[AnyStr], Protocol):
    __slots__ = ()


AnySerializer: TypeAlias = FileSerializer[AnyStr] | AnyStrSerializer[AnyStr] | FullSerializer[AnyStr]


# endregion
