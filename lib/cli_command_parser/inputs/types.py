"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

import logging
import os
from pathlib import Path as _Path
from typing import Union

from ..utils import Bool
from .utils import InputParam, StatMode, FileWrapper, Converter, allows_write

__all__ = ['Path', 'File', 'Serialized', 'Json', 'Pickle']
log = logging.getLogger(__name__)


class Path:
    exists: bool = InputParam(None)
    expand: bool = InputParam(True)
    resolve: bool = InputParam(False)
    type: Union[StatMode, str] = InputParam(StatMode.ANY)
    readable: bool = InputParam(False)
    writable: bool = InputParam(False)
    allow_dash: bool = InputParam(False)

    def __init__(
        self,
        *,
        exists: Bool = None,
        expand: Bool = True,
        resolve: Bool = False,
        type: Union[StatMode, str] = StatMode.ANY,  # noqa
        readable: Bool = False,
        writable: Bool = False,
        allow_dash: Bool = False,
    ):
        """
        :param exists: If set, then the provided path must already exist if True, or must not already exist if False.
          Default: existence is not checked.
        :param expand: Whether tilde (``~``) should be expanded.
        :param resolve: Whether the path should be fully resolved to its absolute path, with symlinks resolved, or not.
        :param type: To restrict the acceptable types of files/directories that are accepted, specify the
          :class:`StatMode` that matches the desired type.  By default, any type is accepted.  To accept specifically
          only regular files or directories, for example, use ``type=StatMode.DIR | StatMode.FILE``.
        :param readable: If True, the path must be readable.
        :param writable: If True, the path must be writable.
        :param allow_dash: Allow a dash (``-``) to be provided to indicate stdin/stdout (default: False).
        """
        self.exists = exists
        self.expand = expand
        self.resolve = resolve
        self.type = StatMode(type)
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
        if self.type != StatMode.ANY and path.exists() and not self.type.matches(path.stat().st_mode):
            raise ValueError(f'expected a {self.type}')
        if self.readable and not os.access(path, os.R_OK):
            raise ValueError('it is not readable')
        if self.writable and not os.access(path, os.W_OK):
            raise ValueError('it is not writable')
        return path


class File(Path):
    # binary: bool = InputParam(False)
    encoding: str = InputParam(None)
    errors: str = InputParam(None)
    lazy: bool = InputParam(True)
    mode: str = InputParam('r')
    # write: bool = InputParam(False)
    # append: bool = InputParam(False)

    def __init__(
        self,
        *,
        # binary: Bool = None,
        encoding: str = None,
        errors: str = None,
        lazy: Bool = True,
        mode: str = 'r',
        **kwargs,
    ):
        """
        :param binary: Set to True to read the file in binary mode and return bytes (default: False / text).
        :param encoding: The encoding to use when reading the file in text mode.  Ignored if the parsed path is ``-``.
        :param errors: Error handling when reading the file in text mode.  Ignored if the parsed path is ``-``.
        :param lazy: If True, a :class:`FileWrapper` will be stored in the Parameter using this File, otherwise the
          file will be read immediately upon parsing of the path argument.
        :param write: Whether the file should be opened for writing (default: False / read only)
        :param append: Whether the file should be opened for appending (implies write)
        :param kwargs: Additional keyword arguments to pass to :class:`.Path`
        """
        if not lazy and allows_write(mode):
            raise ValueError(f'Cannot combine mode={mode!r} with lazy=False for {self.__class__.__name__}')
        super().__init__(**kwargs)
        # self.binary = binary
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.mode = mode

    # @property
    # def _mode(self) -> str:
    #     mode = 'a' if self.append else 'w' if self.write else 'r'
    #     if self.binary:
    #         mode += 'b'
    #     return mode

    def _prep_file_wrapper(self, path: _Path) -> FileWrapper:
        return FileWrapper(path, self.mode, self.encoding, self.errors)

    def __call__(self, value: str) -> Union[FileWrapper, str, bytes]:
        wrapper = self._prep_file_wrapper(super().__call__(value))
        if self.lazy:
            return wrapper
        return wrapper.read()


class Serialized(File):
    converter: Converter = InputParam(None)
    convert_directly: bool = InputParam(False)

    def __init__(self, converter: Converter, *, convert_directly: Bool = False, **kwargs):
        """
        :param converter: Function to use to (de)serialize the given file, such as :func:`python:json.loads`,
          :func:`python:json.dumps`, :func:`python:pickle.load`, etc.
        :param convert_directly: For reading, if True, call the converter with the file object, otherwise read the
          file first and call the converter with the result.  For writing, if True, call the converter with both the
          data to be written and the file object, otherwise call the converter with only the data and then write the
          result to the file.
        :param kwargs: Additional keyword arguments to pass to :class:`.File`
        """
        super().__init__(**kwargs)
        self.converter = converter
        self.convert_directly = convert_directly

    def _prep_file_wrapper(self, path: _Path) -> FileWrapper:
        return FileWrapper(path, self.mode, self.encoding, self.errors, self.converter, self.convert_directly)


class Json(Serialized):
    def __init__(self, *, mode: str = 'rb', **kwargs):
        import json

        write = allows_write(mode, True)
        kwargs['convert_directly'] = write  # json.load just calls loads with f.read()
        super().__init__(json.dump if write else json.loads, mode=mode, **kwargs)


class Pickle(Serialized):
    def __init__(self, *, mode: str = 'rb', **kwargs):
        import pickle

        if 't' in mode:
            raise ValueError(f'Invalid mode={mode!r} - pickle does not read/write text')
        if 'b' not in mode:
            mode += 'b'

        write = allows_write(mode, True)
        # kwargs['binary'] = True
        kwargs['convert_directly'] = True
        super().__init__(pickle.dump if write else pickle.load, mode=mode, **kwargs)
