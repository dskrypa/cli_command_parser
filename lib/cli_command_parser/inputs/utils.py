"""
Utils for input types

:author: Doug Skrypa
"""

import sys
import warnings
from contextlib import contextmanager
from pathlib import Path
from stat import S_IFMT, S_IFDIR, S_IFCHR, S_IFBLK, S_IFREG, S_IFIFO, S_IFLNK, S_IFSOCK
from typing import Union, Callable, Any, TextIO, BinaryIO, ContextManager
from weakref import finalize

from ..utils import Bool, FixedFlag
from .exceptions import InputValidationError

__all__ = ['InputParam', 'StatMode', 'FileWrapper']

FP = Union[TextIO, BinaryIO]
Deserializer = Callable[[Union[str, bytes, FP]], Any]
Serializer = Callable[..., Union[str, bytes, None]]
Converter = Union[Deserializer, Serializer]


class InputParam:
    __slots__ = ('default', 'name')

    def __init__(self, default: Any):
        self.default = default

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance, owner) -> Any:
        if instance is None:
            return self
        try:
            return instance.__dict__[self.name]
        except KeyError:
            return self.default

    def __set__(self, instance, value: Any):
        if value != self.default:
            instance.__dict__[self.name] = value


class StatMode(FixedFlag):
    def __new__(cls, mode, friendly_name):
        # Defined __new__ to avoid juggling dicts for the stat mode values and names
        obj = object.__new__(cls)
        obj.mode = mode
        obj.friendly_name = friendly_name
        if mode is None:  # ANY
            obj._value_ = sum(m._value_ for m in cls.__members__.values())
        else:
            obj._value_ = 2 ** len(cls.__members__)
        return obj

    DIR = S_IFDIR, 'directory'
    FILE = S_IFREG, 'regular file'
    CHARACTER = S_IFCHR, 'character special device file'
    BLOCK = S_IFBLK, 'block special device file'
    FIFO = S_IFIFO, 'FIFO (named pipe)'
    LINK = S_IFLNK, 'symbolic link'
    SOCKET = S_IFSOCK, 'socket'
    ANY = None, 'any'

    def matches(self, mode: int) -> bool:
        mode = S_IFMT(mode)
        return any(mode == part.mode for part in self._decompose())

    def __str__(self) -> str:
        try:
            return self.friendly_name
        except AttributeError:  # Combined flags
            pass
        names = [part.friendly_name for part in self._decompose()]
        if len(names) == 2:
            return '{} or {}'.format(*names)
        names[-1] = f'or {names[-1]}'
        return ', '.join(names)


class FileWrapper:
    def __init__(
        self,
        path: Path,
        mode: str = 'r',
        encoding: str = None,
        errors: str = None,
        converter: Converter = None,
        pass_file: Bool = False,
    ):
        self.path = path
        self.mode = mode
        self.binary = 'b' in mode
        self.encoding = encoding
        self.errors = errors
        self.converter = converter
        self.pass_file = pass_file
        self._fp: Union[TextIO, BinaryIO, None] = None
        self._finalizer = None

    def __eq__(self, other: 'FileWrapper') -> bool:
        attrs = ('path', 'mode', 'binary', 'encoding', 'errors', 'converter', 'pass_file')
        try:
            return all(getattr(self, a) == getattr(other, a) for a in attrs)
        except AttributeError:
            return NotImplemented

    def read(self) -> Any:
        with self._file() as f:
            if self.converter is not None:
                return self.converter(f if self.pass_file else f.read())
            else:
                return f.read()

    def write(self, data: Any):
        with self._file() as f:
            if self.converter is not None:
                if self.pass_file:
                    self.converter(data, f)
                else:
                    f.write(self.converter(data))
            else:
                f.write(data)

    def _open(self) -> FP:
        if self.path == Path('-'):
            stream = sys.stdin if 'r' in self.mode else sys.stdout
            return stream.buffer if self.binary else stream

        try:
            self._fp = fp = self.path.open(self.mode, encoding=self.encoding, errors=self.errors)
        except OSError as e:
            raise InputValidationError(f'Unable to open {self.path} - {e}') from e
        else:
            self._finalizer = finalize(self, self._cleanup, fp, f'Implicitly cleaning up {self.path}')
            return fp

    @classmethod
    def _cleanup(cls, fp: FP, warn_msg: str):
        fp.close()
        warnings.warn(warn_msg, ResourceWarning)

    def _close(self):
        try:
            self._fp.close()
        except AttributeError:
            pass
        finally:
            self._fp = None

    def close(self):
        try:
            do_close = self._finalizer.detach()
        except AttributeError:
            do_close = False
        if do_close:
            self._close()

    @contextmanager
    def _file(self) -> ContextManager[FP]:
        try:
            yield self._open()
        finally:
            self.close()

    def __enter__(self) -> Union[FP, 'FileWrapper']:
        if self.converter is not None:
            return self
        return self._open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def allows_write(mode: str, strict: bool = False) -> bool:
    chars = 'wxa' if strict else 'wxa+'
    return any(c in mode for c in chars)
