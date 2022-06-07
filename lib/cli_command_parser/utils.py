"""
Utilities for extracting types from annotations, finding / storing program metadata, and other misc utilities.

:author: Doug Skrypa
"""

import re
import sys
from collections.abc import Collection, Iterable, Callable
from contextlib import contextmanager
from enum import Flag, _decompose as decompose  # noqa
from inspect import stack, isclass, FrameInfo
from pathlib import Path
from textwrap import dedent
from typing import Any, Union, Optional, Type, TypeVar, Sequence, get_type_hints, Tuple, Dict, List
from string import whitespace, printable
from urllib.parse import urlparse

try:
    from typing import get_origin, get_args as _get_args
except ImportError:  # Added in 3.8; the versions from 3.8 are copied here
    from .compat import get_origin, _get_args

try:
    from types import NoneType
except ImportError:  # Added in 3.10
    NoneType = type(None)

from .exceptions import ParameterDefinitionError

Bool = Union[bool, Any]
_NotSet = object()
FlagEnum = TypeVar('FlagEnum', bound=Union[Flag, 'FlagEnumMixin'])


class cached_class_property(classmethod):
    def __init__(self, func: Callable):
        super().__init__(property(func))  # noqa  # makes Sphinx handle it better than if this was not done
        self.__doc__ = func.__doc__
        self.func = func
        self.values = {}

    def __get__(self, obj: None, cls):  # noqa
        try:
            return self.values[cls]
        except KeyError:
            self.values[cls] = value = self.func(cls)
            return value


def validate_positional(
    param_cls: str, value: str, prefix: str = 'choice', exc: Type[Exception] = ParameterDefinitionError
):
    if not value or value.startswith('-'):
        raise exc(f"Invalid {param_cls} {prefix}={value!r} - may not be empty or start with '-'")

    bad = {c for c in value if (c in whitespace and c != ' ') or c not in printable}
    if bad:
        raise exc(f'Invalid {param_cls} {prefix}={value!r} - invalid characters: {bad}')


class ProgramMetadata:
    description: Optional[str] = None

    def __init__(
        self,
        prog: str = None,
        *,
        url: str = None,
        docs_url: str = None,
        email: str = None,
        version: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        doc_name: str = None,
        doc: str = None,
    ):
        self._cmd_args = {
            'prog': prog,
            'url': url,
            'docs_url': docs_url,
            'email': email,
            'version': version,
            'doc_name': doc_name,
        }
        self._init(ProgInfo())
        self.doc_name = doc_name
        self.usage = usage
        self.epilog = epilog
        if description:
            self.description = description
        elif doc:
            doc = dedent(doc).lstrip()
            if doc.strip():  # avoid space-only doc, but let possibly intentional trailing spaces / newlines to persist
                self.description = doc

    def _init(self, info: 'ProgInfo'):
        a = self._cmd_args
        self.path = info.path
        self.prog = a['prog'] or info.path.name
        docs_url_from_repo_url = self._docs_url_from_repo_url
        self.docs_url = a['docs_url'] or docs_url_from_repo_url(a['url']) or docs_url_from_repo_url(info.repo_url)
        self.url = a['url'] or info.repo_url
        self.email = a['email'] or info.email
        self.version = a['version'] or info.version or ''
        self.doc_str = info.doc_str
        self.doc_name = a['doc_name']

    @property
    def doc_name(self) -> str:
        return self._doc_name

    @doc_name.setter
    def doc_name(self, value: Optional[str]):
        if value:
            self._doc_name = value
        elif self.path.name != ProgInfo.default_file_name:
            self._doc_name = self.path.stem
        else:
            self._doc_name = self.prog

    def _docs_url_from_repo_url(self, repo_url: Optional[str]):  # noqa
        try:  # Note: This is only done this way to address a false positive on a GitHub security scan
            parsed = urlparse(repo_url)
            if parsed.scheme == 'https' and parsed.hostname == 'github.com':
                user, repo = parsed.path[1:].split('/')
                return f'https://{user}.github.io/{repo}/'
        except Exception:  # noqa
            pass
        return None

    def format_epilog(self, extended: Bool = True) -> str:
        parts = [self.epilog] if self.epilog else []
        if parts and not extended:
            return parts[0]

        version = self.version
        if version:
            version = f' [ver. {version}]'
        if self.email:
            parts.append(f'Report {self.prog}{version} bugs to {self.email}')
        url = self.docs_url or self.url
        if url:
            parts.append(f'Online documentation: {url}')
        return '\n\n'.join(parts)


class ProgInfo:
    __dynamic_import: Optional[Tuple[Path, Dict[str, Any]]] = None
    default_file_name: str = 'UNKNOWN'  #: Default name used when it cannot be determined from the stack or sys.argv
    installed_via_setup: bool = False
    email: Optional[str] = None
    version: Optional[str] = None
    repo_url: Optional[str] = None
    path: Optional[Path] = None
    doc_str: Optional[str] = None

    def __init__(self):
        self.path, g = self._path_and_globals()
        self.email = g.get('__author_email__')
        self.version = g.get('__version__')
        self.repo_url = g.get('__url__')
        self.doc_str = g.get('__doc__')

    def __repr__(self) -> str:
        return (
            f'<ProgInfo[path={self.path.as_posix()}, email={self.email!r}, version={self.version},'
            f' url={self.repo_url!r}, doc_str={self.doc_str!r}]>'
        )

    @classmethod
    def _print_stack_info(cls):
        for i, level in reversed(tuple(enumerate(stack()))):
            g = level.frame.f_globals
            print(
                f'\n[{i:02d}] {level.filename}:{level.lineno} fn={level.function}:'
                f'\n    __package__={g["__package__"]!r}'
                f'\n    {", ".join(sorted(g))}'
            )

    @classmethod
    @contextmanager
    def _dynamic_import(cls, path: Path, module_globals: Dict[str, Any]):
        cls.__dynamic_import = path, module_globals
        try:
            yield
        finally:
            cls.__dynamic_import = None

    def _path_and_globals(self) -> Tuple[Path, Dict[str, Any]]:
        if self.__dynamic_import:
            return self.__dynamic_import
        try:
            top_level, g = self._find_top_frame_and_globals()
            return self._resolve_path(top_level.filename), g
        except Exception as e:  # noqa
            return self._resolve_path(), {}

    def _resolve_path(self, path: str = None) -> Path:
        from_setup = path and self.installed_via_setup and path.endswith('-script.py')
        if path and not from_setup:
            return Path(path)

        try:
            name = sys.argv[0]
        except IndexError:
            if from_setup:
                path = Path(path)
                return path.with_name(path.stem[:-7] + '.py')
            else:
                return Path.cwd().joinpath(self.default_file_name)

        argv_path = Path(name)
        try:
            if argv_path.is_file():
                return argv_path
        except OSError:
            pass

        return Path.cwd().joinpath(self.default_file_name)

    def _find_cmd_frame_info(self, fi_stack: Sequence[FrameInfo]) -> FrameInfo:
        if not self.installed_via_setup:
            return fi_stack[-1]

        this_pkg = __package__.split('.', 1)[0]
        # ignore_pkgs = {this_pkg, '', 'IPython', 'IPython.core', 'IPython.terminal', 'traitlets.config'}
        this_pkg_dot = this_pkg + '.'
        for level in reversed(fi_stack[:-1]):
            pkg = level.frame.f_globals.get('__package__') or ''
            if pkg != this_pkg and not pkg.startswith(this_pkg_dot):  # Exclude intermediate frames in this package
                return level

        return fi_stack[-1]

    def _detect_install_type(self, fi_stack: Sequence[FrameInfo]):
        top_level = fi_stack[-1]
        g = top_level.frame.f_globals
        self.installed_via_setup = 'load_entry_point' in g and 'main' not in g

    def _find_top_frame_and_globals(self) -> Tuple[FrameInfo, Dict[str, Any]]:
        fi_stack = stack()
        # TODO: Find globals for the module the Command is in instead
        self._detect_install_type(fi_stack)
        cmd_frame_info = self._find_cmd_frame_info(fi_stack)
        return fi_stack[-1], cmd_frame_info.frame.f_globals


def camel_to_snake_case(text: str, delim: str = '_') -> str:
    return ''.join(f'{delim}{c}' if i and c.isupper() else c for i, c in enumerate(text)).lower()


# region Annotation Inspection


def get_descriptor_value_type(command_cls: type, attr: str) -> Optional[type]:
    try:
        annotation = get_type_hints(command_cls)[attr]
    except KeyError:
        return None

    return get_annotation_value_type(annotation)


def get_annotation_value_type(annotation) -> Optional[type]:
    origin = get_origin(annotation)
    """
    Note on get_origin return values:
    get_origin(List[str]) -> list
    get_origin(List) -> list
    get_origin(list[str]) -> list
    get_origin(list) -> None
    """
    if origin is None and isinstance(annotation, type):
        return annotation
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, annotation)
    elif origin is Union:
        return _type_from_union(annotation)
    return None


def get_args(annotation) -> tuple:
    """
    Wrapper around :func:`python:typing.get_args` for 3.7~8 compatibility, to make it behave more like it does in 3.9+
    """
    if getattr(annotation, '_special', False):  # 3.7-3.8 generic collection alias with no content types
        return ()
    return _get_args(annotation)


def _type_from_union(annotation) -> Optional[type]:
    args = get_args(annotation)
    # Note: Unions of a single argument return the argument; i.e., Union[T] returns T, so the len can never be 1
    if len(args) == 2 and NoneType in args:
        arg = args[0] if args[1] is NoneType else args[1]
    else:
        return None

    origin = get_origin(arg)
    if origin is None and isinstance(arg, type):
        return arg
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, arg)
    else:
        return None


def _type_from_collection(origin, annotation) -> Optional[type]:
    args = get_args(annotation)
    try:
        annotation = args[0]
    except IndexError:  # The annotation was a collection with no content types specified
        return origin

    n_args = len(args)
    if n_args > 2 or (n_args > 1 and (origin is not tuple or args[1] is not Ellipsis)):
        return None

    origin = get_origin(annotation)
    if origin is None and isinstance(annotation, type):
        return annotation
    elif origin is Union:
        return _type_from_union(annotation)
    else:
        return None


# endregion


def is_numeric(text: str) -> Bool:
    try:
        num_match = is_numeric._num_match
    except AttributeError:
        is_numeric._num_match = num_match = re.compile(r'^-\d+$|^-\d*\.\d+?$').match
    return num_match(text)


class FlagEnumMixin:
    @classmethod
    def _missing_(cls: Type[FlagEnum], value) -> FlagEnum:
        if isinstance(value, str):
            if value.startswith(('!', '~')):
                invert = True
                value = value[1:]
            else:
                invert = False

            try:
                member = cls._missing_str(value)
            except KeyError:
                expected = ', '.join(cls._member_map_)
                raise ValueError(f'Invalid {cls.__name__} value={value!r} - expected one of {expected}') from None
            else:
                return ~member if invert else member

        return super()._missing_(value)  # noqa

    @classmethod
    def _missing_str(cls: Type[FlagEnum], value: str) -> FlagEnum:
        try:
            return cls._member_map_[value.upper()]  # noqa
        except KeyError:
            pass
        if '|' in value:
            tmp = cls(0)
            for part in map(str.strip, value.split('|')):
                if not part:
                    continue
                try:
                    tmp |= cls._member_map_[part.upper()]
                except KeyError:
                    break
            else:
                if tmp._value_ != 0:
                    return tmp

        raise KeyError

    def _decompose(self: FlagEnum) -> List[FlagEnum]:
        if self._name_ is None:
            return sorted(decompose(self.__class__, self.value)[0])
        return [self]

    def __repr__(self: FlagEnum) -> str:
        names = '|'.join(part._name_ for part in self._decompose())
        return f'<{self.__class__.__name__}:{names}>'

    def __lt__(self: FlagEnum, other: FlagEnum) -> bool:
        return self._value_ < other._value_
