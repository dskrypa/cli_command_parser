"""
Utils for input types

:author: Doug Skrypa
"""

from __future__ import annotations

import sys
import warnings
from contextlib import contextmanager
from pathlib import Path
from stat import S_IFBLK, S_IFCHR, S_IFDIR, S_IFIFO, S_IFLNK, S_IFMT, S_IFREG, S_IFSOCK
from typing import TYPE_CHECKING, Any, BinaryIO, ContextManager, TextIO, Union
from weakref import finalize

from ..utils import FixedFlag
from .exceptions import InputValidationError

if TYPE_CHECKING:
    from ..typing import FP, Bool, Converter, Number

__all__ = ['InputParam', 'StatMode', 'FileWrapper', 'fix_windows_path', 'range_str', 'RangeMixin']


class InputParam:
    __slots__ = ('default', 'name')

    def __init__(self, default: Any):
        self.default = default

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance, owner) -> Any:
        try:
            return instance.__dict__[self.name]
        except AttributeError:  # instance is None
            return self
        except KeyError:
            return self.default

    def __set__(self, instance, value: Any):
        if value != self.default:
            instance.__dict__[self.name] = value


class StatMode(FixedFlag):
    def __new__(cls, mode, friendly_name: str = None):
        # Defined __new__ to avoid juggling dicts for the stat mode values and names
        obj = object.__new__(cls)
        if friendly_name:
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
            name = self.friendly_name
        except AttributeError:  # Combined flags
            name = None
        if name:
            return name
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
        parents: Bool = False,
    ):
        self.path = path
        self.mode = mode
        self.binary = 'b' in mode
        self.encoding = encoding
        self.errors = errors
        self.converter = converter
        self.pass_file = pass_file
        self.parents = parents
        self._fp: Union[TextIO, BinaryIO, None] = None
        self._finalizer = None

    def __eq__(self, other: FileWrapper) -> bool:
        attrs = ('path', 'mode', 'binary', 'encoding', 'errors', 'converter', 'pass_file', 'parents')
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

        if self.parents and allows_write(self.mode):
            self.path.parent.mkdir(parents=True, exist_ok=True)

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

    def __enter__(self) -> Union[FP, FileWrapper]:
        if self.converter is not None:
            return self
        return self._open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def allows_write(mode: str, strict: bool = False) -> bool:
    chars = 'wxa' if strict else 'wxa+'
    return any(c in mode for c in chars)


def fix_windows_path(path: Path) -> Path:
    """
    Attempts to resolve issues related to inconsistencies between the way the version of Bash that is distributed with
    Git handles paths in some situations and the way that Python handles paths.

    The use case that this function currently handles is when the given Path does not exist, and it was auto-completed
    by Git Bash to begin with ``/{drive}/...`` instead of ``{drive}:/...``.
    """
    if path.exists() or not path.as_posix().startswith('/'):
        return path

    try:
        _, drive_letter, *parts = path.parts
    except ValueError:
        return path

    if len(drive_letter) != 1:
        return path

    drive = drive_letter.upper() + ':/'
    alt_path = Path(drive, *parts)
    if alt_path.exists() or (Path(drive).exists() and not Path(f'/{drive_letter}/').exists()):
        return alt_path
    else:
        return path


def range_str(min_val: Number, max_val: Number, include_min: Bool, include_max: Bool, var: str = 'N') -> str:
    if min_val is not None:
        min_str = f'{min_val} {"<=" if include_min else "<"} '
    else:
        min_str = ''

    if max_val is not None:
        max_str = f' {"<=" if include_max else "<"} {max_val}'
    else:
        max_str = ''

    return f'{min_str}{var}{max_str}'


class RangeMixin:
    __slots__ = ()  # It isn't possible to use 2+ bases when they both have content in __slots__
    min: Number
    max: Number
    include_min: bool
    include_max: bool

    def value_lt_min(self, value: Number) -> bool:
        if self.min is not None:
            # Bad if < when inclusive, bad if <= when exclusive
            return (value < self.min) if self.include_min else (value <= self.min)
        return False

    def value_gt_max(self, value: Number) -> bool:
        if self.max is not None:
            return (value > self.max) if self.include_max else (value >= self.max)
        return False
