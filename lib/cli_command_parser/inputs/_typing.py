from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any, Callable, Sequence, TypeAlias, TypeVar, Union

if TYPE_CHECKING:
    from datetime import date, datetime, time, timedelta
    from numbers import Number as _Number


Deserializer: TypeAlias = Callable[[str | bytes | IO], Any]
Serializer: TypeAlias = Callable[[Any, IO], None] | Callable[[Any], str | bytes]
Converter: TypeAlias = Deserializer | Serializer

Locale = str | tuple[str | None, str | None]
TimeBound: TypeAlias = Union['datetime', 'date', 'time', 'timedelta', None]

N = TypeVar('N', bound=Union['_Number', int, float])
Number: TypeAlias = N | None
NumType: TypeAlias = Callable[[str | Any], N]
RngType: TypeAlias = range | int | Sequence[int]
