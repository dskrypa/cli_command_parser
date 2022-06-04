"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

import logging
import os
import sys
from enum import Flag, auto, _decompose as decompose  # noqa
from pathlib import Path as _Path
from stat import S_IFMT, S_IFDIR, S_IFCHR, S_IFBLK, S_IFREG, S_IFIFO, S_IFLNK, S_IFSOCK
from typing import Union, Callable, Any

from .utils import Bool

__all__ = ['StatMode', 'Path', 'File', 'Deserialized', 'Json']
log = logging.getLogger(__name__)

MODE_MAP = {
    'DIR': S_IFDIR,
    'FILE': S_IFREG,
    'CHARACTER': S_IFCHR,
    'BLOCK': S_IFBLK,
    'FIFO': S_IFIFO,
    'LINK': S_IFLNK,
    'SOCKET': S_IFSOCK,
}


# noinspection PyArgumentList
class StatMode(Flag):
    ANY = auto()
    DIR = auto()
    FILE = auto()
    CHARACTER = auto()
    BLOCK = auto()
    FIFO = auto()
    LINK = auto()
    SOCKET = auto()

    def matches(self, mode: int) -> bool:
        mode = S_IFMT(mode)
        for part in decompose(StatMode, self.value)[0]:
            if mode == MODE_MAP[part.name]:
                return True
        return False

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper()]
            except KeyError:
                pass
        return super()._missing_(value)


class Path:
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
                raise ValueError(f'Invalid path={path} - it does not exist')
            elif not self.exists and path.exists():
                raise ValueError(f'Invalid path={path} - it already exists')
        if self.mode != StatMode.ANY and path.exists() and not self.mode.matches(path.stat().st_mode):
            raise ValueError(f'Invalid path={path} - expected mode={self.mode}')
        if self.readable and not os.access(path, os.R_OK):
            raise ValueError(f'Invalid path={path} - it is not readable')
        if self.writable and not os.access(path, os.W_OK):
            raise ValueError(f'Invalid path={path} - it is not readable')
        return path


class File(Path):
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
    def __init__(self, deserializer: Callable[[Union[str, bytes]], Any], **kwargs):
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
