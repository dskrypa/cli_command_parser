"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

import logging
import os
import sys
from enum import Flag, _decompose as decompose  # noqa
from pathlib import Path as _Path
from stat import S_IFMT, S_IFDIR, S_IFCHR, S_IFBLK, S_IFREG, S_IFIFO, S_IFLNK, S_IFSOCK
from typing import Union, Callable, Any, List

from .utils import Bool

__all__ = ['StatMode', 'Path', 'File', 'Deserialized', 'Json']
log = logging.getLogger(__name__)

Deserializer = Callable[[Union[str, bytes]], Any]


class StatMode(Flag):
    def __new__(cls, mode, friendly_name):
        # Defined __new__ to avoid juggling dicts for the stat mode values and names
        obj = object.__new__(cls)
        if mode is None:  # ANY
            obj._value_ = sum(m._value_ for m in cls.__members__.values())
        else:
            obj._value_ = 2 ** len(cls.__members__)
        obj.mode = mode
        obj.friendly_name = friendly_name
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

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper()]
            except KeyError:
                pass
        return super()._missing_(value)

    def _decompose(self) -> List['StatMode']:
        if self._name_ is None:
            return sorted(decompose(StatMode, self.value)[0])
        return [self]

    def __repr__(self) -> str:
        names = '|'.join(part._name_ for part in self._decompose())
        return f'<{self.__class__.__name__}:{names}>'

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

    def __lt__(self, other: 'StatMode') -> bool:
        return self._value_ < other._value_


class InputParam:
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


class Path:
    exists: bool = InputParam(None)
    expand: bool = InputParam(True)
    resolve: bool = InputParam(False)
    mode: Union[StatMode, str] = InputParam(StatMode.ANY)
    readable: bool = InputParam(False)
    writable: bool = InputParam(False)
    allow_dash: bool = InputParam(False)

    def __init__(
        self,
        *,
        exists: Bool = None,
        expand: Bool = True,
        resolve: Bool = False,
        mode: Union[StatMode, str] = StatMode.ANY,
        readable: Bool = False,
        writable: Bool = False,
        allow_dash: Bool = False,
    ):
        """
        :param exists: If set, then the provided path must already exist if True, or must not already exist if False.
          Default: existence is not checked.
        :param expand: Whether tilde (``~``) should be expanded.
        :param resolve: Whether the path should be fully resolved to its absolute path, with symlinks resolved, or not.
        :param mode: To restrict the acceptable types of files/directories that are accepted, specify the
          :class:`StatMode` that matches the desired type.  By default, any type is accepted.  To accept specifically
          only regular files or directories, for example, use ``mode=StatMode.DIR | StatMode.FILE``.
        :param readable: If True, the path must be readable.
        :param writable: If True, the path must be writable.
        :param allow_dash: Allow a dash (``-``) to be provided to indicate stdin/stdout (default: False).
        """
        self.exists = exists
        self.expand = expand
        self.resolve = resolve
        self.mode = StatMode(mode)
        self.readable = readable
        self.writable = writable
        self.allow_dash = allow_dash

    def __repr__(self) -> str:
        non_defaults = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'<{self.__class__.__name__}({non_defaults})>'

    def __call__(self, value: str) -> _Path:
        value = value.strip()
        if not value:
            raise ValueError('A valid path is required')
        path = _Path(value)
        if value == '-':
            if self.allow_dash:
                return path
            raise ValueError('Dash (-) is not supported for this parameter')

        if self.expand:
            path = path.expanduser()
        if self.resolve:
            path = path.resolve()
        if self.exists is not None:
            if self.exists and not path.exists():
                raise ValueError('it does not exist')
            elif not self.exists and path.exists():
                raise ValueError('it already exists')
        if self.mode != StatMode.ANY and path.exists() and not self.mode.matches(path.stat().st_mode):
            raise ValueError(f'expected a {self.mode}')
        if self.readable and not os.access(path, os.R_OK):
            raise ValueError('it is not readable')
        if self.writable and not os.access(path, os.W_OK):
            raise ValueError('it is not writable')
        return path


class File(Path):
    binary: bool = InputParam(False)
    encoding: str = InputParam(None)
    errors: str = InputParam(None)

    def __init__(self, *, binary: Bool = False, encoding: str = None, errors: str = None, **kwargs):
        """
        :param binary: Set to True to read the file in binary mode and return bytes (default: False / text).
        :param encoding: The encoding to use when reading the file in text mode.
        :param errors: Error handling when reading the file in text mode.
        :param kwargs: Additional keyword arguments to pass to :class:`.Path`
        """
        super().__init__(**kwargs)
        self.binary = binary
        self.encoding = encoding
        self.errors = errors

    def __call__(self, value: str) -> Union[str, bytes]:
        path = super().__call__(value)
        if path == _Path('-'):
            return sys.stdin.read()
        elif self.binary:
            return path.read_bytes()
        return path.read_text(self.encoding, self.errors)


class Deserialized(File):
    encoding: Deserializer = InputParam(None)

    def __init__(self, deserializer: Deserializer, **kwargs):
        """
        :param deserializer: Function to use to deserialize the given file, such as :func:`python:json.loads`,
          :func:`python:pickle.loads`, etc.
        :param kwargs: Additional keyword arguments to pass to :class:`.File`
        """
        super().__init__(**kwargs)
        self.deserializer = deserializer

    def __call__(self, value: str) -> Any:
        data = super().__call__(value)
        return self.deserializer(data)


class Json(File):
    def __call__(self, value: str) -> Any:
        import json

        path = Path.__call__(self, value)
        with path.open('rb' if self.binary else 'r', encoding=self.encoding, errors=self.errors) as f:
            return json.load(f)
