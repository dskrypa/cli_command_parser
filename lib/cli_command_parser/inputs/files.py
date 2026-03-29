"""
Custom file / path input handlers for Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import os
from abc import ABC
from pathlib import Path as _Path
from typing import TYPE_CHECKING, Any, AnyStr, Literal, TypeVar, overload

from ..typing import T
from .base import InputType
from .exceptions import InputValidationError
from .utils import (
    FileWrapper,
    InputParam,
    JsonSerializer,
    SerializedFileWrapper,
    StatMode,
    allows_write,
    fix_windows_path,
)

if TYPE_CHECKING:
    from ..typing import Bool, OptStr, PathLike
    from ._typing import AnySerializer, OpenAnyMode, OpenBinaryMode, OpenTextMode

__all__ = ['Path', 'File', 'Serialized', 'Json', 'Pickle']

T_co = TypeVar('T_co', covariant=True)


class FileInput(InputType[T], ABC):
    exists: InputParam[bool | None] = InputParam(None)
    expand: InputParam[bool] = InputParam(True)
    resolve: InputParam[bool] = InputParam(False)
    type: InputParam[StatMode] = InputParam(StatMode.ANY)
    readable: InputParam[bool] = InputParam(False)
    writable: InputParam[bool] = InputParam(False)
    allow_dash: InputParam[bool] = InputParam(False)
    use_windows_fix: InputParam[bool] = InputParam(True)

    def __init__(
        self,
        *,
        exists: Bool = None,
        expand: Bool = True,
        resolve: Bool = False,
        type: StatMode | str = StatMode.ANY,  # noqa
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
        self.type = StatMode(type)
        self.readable = readable
        self.writable = writable
        self.allow_dash = allow_dash
        self.use_windows_fix = use_windows_fix

    def __repr__(self) -> str:
        non_defaults = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'<{self.__class__.__name__}({non_defaults})>'

    def fix_default(self, value: T | str | None) -> T | str | None:
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
                raise InputValidationError('the provided path does not exist')
            elif not self.exists and path.exists():
                raise InputValidationError('the provided path already exists')

        if self.type != StatMode.ANY and path.exists() and not self.type.matches(path.stat().st_mode):
            # TODO: Indicate what the discovered type was
            raise InputValidationError(f'expected a {self.type}')

        if self.readable and not os.access(path, os.R_OK):
            raise InputValidationError('the provided path is not readable')

        if self.writable and not os.access(path, os.W_OK):
            raise InputValidationError('the provided path is not writable')

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


class File(FileInput[T_co]):
    """
    :param mode: The mode in which the file should be opened.  For more info, see :func:`python:open`.
    :param encoding: The encoding to use when reading the file in text mode.  Ignored if the parsed path is ``-``.
    :param errors: Error handling when reading the file in text mode.  Ignored if the parsed path is ``-``.
    :param lazy: If True, a :class:`FileWrapper` will be stored in the Parameter using this File, otherwise the
      file will be read immediately upon parsing of the path argument.
    :param parents: If True and ``mode`` implies writing, then create parent directories as needed.  Ignored otherwise.
    :param kwargs: Additional keyword arguments to pass to :class:`.Path`.
    """

    mode: InputParam[OpenAnyMode] = InputParam('r')
    type: InputParam[StatMode] = InputParam(StatMode.FILE)
    encoding: InputParam[str | None] = InputParam(None)
    errors: InputParam[str | None] = InputParam(None)
    lazy: InputParam[bool] = InputParam(True)
    parents: InputParam[bool] = InputParam(False)

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: File[FileWrapper[str]],
            mode: OpenTextMode = 'r',
            *,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[True] = True,
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: File[FileWrapper[bytes]],
            mode: OpenBinaryMode,
            *,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[True] = True,
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: File[str],
            mode: OpenTextMode = 'r',
            *,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[False],
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: File[bytes],
            mode: OpenBinaryMode,
            *,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[False],
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self,
            mode: OpenAnyMode = 'r',
            *,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Bool = True,
            parents: Bool = False,
        ): ...

    def __init__(
        self,
        mode: OpenAnyMode = 'r',
        *,
        encoding: OptStr = None,
        errors: OptStr = None,
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
        return FileWrapper(path, self.mode, encoding=self.encoding, errors=self.errors, parents=self.parents)

    def __call__(self, value: PathLike) -> T_co:
        wrapper = self._prep_file_wrapper(self.validated_path(value))
        if self.lazy:
            return wrapper  # type: ignore[return-value]
        return wrapper.read()


class Serialized(File[T_co]):
    """
    :param serializer: Class or module that provides ``load``/``dump`` and/or ``loads``/``dumps`` methods/functions for
      deserialization and serialization, respectively.  Expects them to follow the same interface as the *json* or
      *pickle* modules, with :func:`python:json.loads`, :func:`python:json.dumps`, :func:`python:pickle.load`, etc.
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    serializer: AnySerializer

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: Serialized[SerializedFileWrapper[AnyStr]],
            serializer: AnySerializer[AnyStr],
            *,
            mode: OpenAnyMode = 'r',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[True] = True,
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: Serialized[Any],
            serializer: AnySerializer,
            *,
            mode: OpenAnyMode = 'r',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[False],
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self,
            serializer: AnySerializer,
            *,
            mode: OpenAnyMode = 'r',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Bool = True,
            parents: Bool = False,
        ): ...

    def __init__(self, serializer: AnySerializer, **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer

    def __repr__(self) -> str:
        non_defaults = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if k != 'serializer')
        # `serializer` must be excluded to prevent infinite recursion when an instance method is stored in that attr
        return f'<{self.__class__.__name__}({non_defaults})>'

    def _prep_file_wrapper(self, path: _Path) -> SerializedFileWrapper[AnyStr]:
        return SerializedFileWrapper(
            path,
            self.mode,
            serializer=self.serializer,
            encoding=self.encoding,
            errors=self.errors,
            parents=self.parents,
        )


class Json(Serialized[T_co]):
    """
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: Json[SerializedFileWrapper[str]],
            *,
            mode: OpenTextMode = 'r',
            wrap_errors: Bool = True,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[True] = True,
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: Json[Any],
            *,
            mode: OpenTextMode = 'r',
            wrap_errors: Bool = True,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[False],
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self,
            *,
            mode: OpenTextMode = 'r',
            wrap_errors: Bool = True,
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Bool = True,
            parents: Bool = False,
        ): ...

    def __init__(self, *, mode: OpenTextMode = 'r', wrap_errors: Bool = True, **kwargs):
        super().__init__(JsonSerializer(wrap_errors), mode=mode, **kwargs)


class Pickle(Serialized[T_co]):
    """
    :param kwargs: Additional keyword arguments to pass to :class:`.File`
    """

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: Pickle[SerializedFileWrapper[bytes]],
            *,
            mode: OpenBinaryMode = 'rb',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[True] = True,
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self: Pickle[Any],
            *,
            mode: OpenBinaryMode = 'rb',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Literal[False],
            parents: Bool = False,
        ): ...

        @overload
        def __init__(
            self,
            *,
            mode: OpenBinaryMode = 'rb',
            exists: Bool = None,
            expand: Bool = True,
            resolve: Bool = False,
            type: StatMode | str = StatMode.FILE,  # noqa
            readable: Bool = False,
            writable: Bool = False,
            allow_dash: Bool = False,
            use_windows_fix: Bool = True,
            fix_default: Bool = True,
            encoding: OptStr = None,
            errors: OptStr = None,
            lazy: Bool = True,
            parents: Bool = False,
        ): ...

    def __init__(self, *, mode: OpenBinaryMode = 'rb', **kwargs):
        import pickle

        if 't' in mode or 'b' not in mode:
            raise ValueError(f'Invalid {mode=} - pickle does not read/write text - it requires a binary open mode')

        super().__init__(pickle, mode=mode, **kwargs)
