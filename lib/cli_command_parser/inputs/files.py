"""
Custom file / path input handlers for Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import os
from abc import ABC
from pathlib import Path as _Path
from typing import Optional, Union

from ..typing import FP, Bool, Converter, PathLike, T
from .base import InputType
from .exceptions import InputValidationError
from .utils import FileWrapper, InputParam, StatMode, allows_write, fix_windows_path

__all__ = ['Path', 'File', 'Serialized', 'Json', 'Pickle']


class FileInput(InputType[T], ABC):
    exists: bool = InputParam(None)
    expand: bool = InputParam(True)
    resolve: bool = InputParam(False)
    type: StatMode = InputParam(StatMode.ANY)
    readable: bool = InputParam(False)
    writable: bool = InputParam(False)
    allow_dash: bool = InputParam(False)
    use_windows_fix: bool = InputParam(True)

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
        use_windows_fix: Bool = True,
        fix_default: Bool = True,
    ):
        super().__init__(fix_default)
        self.exists = exists
        self.expand = expand
        self.resolve = resolve
        self.type = StatMode(type)  # pylint: disable=E1120
        self.readable = readable
        self.writable = writable
        self.allow_dash = allow_dash
        self.use_windows_fix = use_windows_fix

    def __repr__(self) -> str:
        non_defaults = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'<{self.__class__.__name__}({non_defaults})>'

    def fix_default(self, value: Optional[T]) -> Optional[T]:
        """
        Fixes the default value to conform to the expected return type for this input.  Allows the default value for a
        path to be provided as a string, for example.
        """
        if value is None or not self._fix_default:
            return value
        return self(value)

    def validated_path(self, path: PathLike) -> _Path:
        if not isinstance(path, _Path):
            if not (path := path.strip()):
                raise InputValidationError('A valid path is required')
            path = _Path(path)
        if path.parts == ('-',):
            if not self.allow_dash:
                raise InputValidationError('Dash (-) is not supported for this parameter')
            return path
        if self.use_windows_fix and os.name == 'nt':
            try:
                path = fix_windows_path(path)
            except OSError:
                pass
        if self.expand:
            path = path.expanduser()
        if self.resolve:
            path = path.resolve()
        if self.exists is not None:
            if self.exists and not path.exists():
                raise InputValidationError('it does not exist')
            elif not self.exists and path.exists():
                raise InputValidationError('it already exists')
        if self.type != StatMode.ANY and path.exists() and not self.type.matches(path.stat().st_mode):
            raise InputValidationError(f'expected a {self.type}')
        if self.readable and not os.access(path, os.R_OK):
            raise InputValidationError('it is not readable')
        if self.writable and not os.access(path, os.W_OK):
            raise InputValidationError('it is not writable')
        return path


class Path(FileInput[_Path]):
    # noinspection PyUnresolvedReferences
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
    :param use_windows_fix: If True (the default) and the program is running on Windows, then :func:`.fix_windows_path`
      will be called to fix issues caused by auto-completion via Git Bash.
    :param fix_default: Whether default values should be normalized using :meth:`~FileInput.fix_default`.
    """

    def __call__(self, value: PathLike) -> _Path:
        return self.validated_path(value)


class File(FileInput[Union[FileWrapper, str, bytes]]):
    """
    :param mode: The mode in which the file should be opened.  For more info, see :func:`python:open`.
    :param encoding: The encoding to use when reading the file in text mode.  Ignored if the parsed path is ``-``.
    :param errors: Error handling when reading the file in text mode.  Ignored if the parsed path is ``-``.
    :param lazy: If True, a :class:`FileWrapper` will be stored in the Parameter using this File, otherwise the
      file will be read immediately upon parsing of the path argument.
    :param parents: If True and ``mode`` implies writing, then create parent directories as needed.  Ignored otherwise.
    :param kwargs: Additional keyword arguments to pass to :class:`.Path`.
    """

    mode: str = InputParam('r')
    type: StatMode = InputParam(StatMode.FILE)
    encoding: str = InputParam(None)
    errors: str = InputParam(None)
    lazy: bool = InputParam(True)
    parents: bool = InputParam(False)

    def __init__(
        self,
        mode: str = 'r',
        *,
        encoding: str = None,
        errors: str = None,
        lazy: Bool = True,
        parents: Bool = False,
        **kwargs,
    ):
        if not lazy and allows_write(mode):
            raise ValueError(f'Cannot combine {mode=} with lazy=False for {self.__class__.__name__}')
        if not allows_write(mode):
            kwargs.setdefault('exists', True)
        kwargs.setdefault('type', StatMode.FILE)
        super().__init__(**kwargs)
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.parents = parents

    def _prep_file_wrapper(self, path: _Path) -> FileWrapper:
        return FileWrapper(path, self.mode, self.encoding, self.errors, parents=self.parents)

    def __call__(self, value: PathLike) -> Union[FileWrapper, str, bytes]:
        wrapper = self._prep_file_wrapper(self.validated_path(value))
        if self.lazy:
            return wrapper
        return wrapper.read()


class Serialized(File):
    """
    :param converter: Function to use to (de)serialize the given file, such as :func:`python:json.loads`,
      :func:`python:json.dumps`, :func:`python:pickle.load`, etc.
    :param pass_file: For reading, if True, call the converter with the file object, otherwise read the
      file first and call the converter with the result.  For writing, if True, call the converter with both the
      data to be written and the file object, otherwise call the converter with only the data and then write the
      result to the file.
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    converter: Converter = InputParam(None)
    pass_file: bool = InputParam(False)

    def __init__(self, converter: Converter, *, pass_file: Bool = False, **kwargs):
        super().__init__(**kwargs)
        self.converter = converter
        self.pass_file = pass_file

    def _prep_file_wrapper(self, path: _Path) -> FileWrapper:
        return FileWrapper(path, self.mode, self.encoding, self.errors, self.converter, self.pass_file, self.parents)


class Json(Serialized):
    """
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    def __init__(self, *, mode: str = 'rb', wrap_errors: bool = True, **kwargs):
        import json

        write = allows_write(mode, True)
        kwargs['pass_file'] = True
        super().__init__(json.dump if write else self._load_json, mode=mode, **kwargs)
        self.wrap_errors = wrap_errors

    def _load_json(self, f: FP):
        from json import JSONDecodeError, load

        try:
            return load(f)
        except JSONDecodeError as e:
            if self.wrap_errors:
                if name := getattr(f, 'name', None):
                    msg = f'json from file={name!r} - are you sure it contains properly formatted json?'
                else:
                    msg = "the provided json content - are you sure it's properly formatted json?"
                raise InputValidationError(f'Unable to load {msg} - error: {e}') from e
            else:
                raise


class Pickle(Serialized):
    """
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    def __init__(self, *, mode: str = 'rb', **kwargs):
        import pickle

        if 't' in mode:
            raise ValueError(f'Invalid {mode=} - pickle does not read/write text')
        if 'b' not in mode:
            mode += 'b'

        write = allows_write(mode, True)
        kwargs['pass_file'] = True
        super().__init__(pickle.dump if write else pickle.load, mode=mode, **kwargs)
