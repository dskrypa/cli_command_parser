"""
:author: Doug Skrypa
"""

import re
import sys
from collections.abc import Collection, Iterable, Callable
from inspect import stack, getsourcefile, isclass
from pathlib import Path
from typing import Any, Union, Optional, Type, get_type_hints
from string import whitespace, printable

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
    ):
        try:
            found_email, found_version, found_url, path = self._find_info()
        except Exception:  # noqa
            path = Path(__file__)
            found_email, found_version, found_url = None, None, None

        self.path = path
        self.prog = prog or path.name
        docs_url_from_repo_url = self._docs_url_from_repo_url
        self.docs_url = docs_url or docs_url_from_repo_url(url) or docs_url_from_repo_url(found_url)
        self.url = url or found_url
        self.email = email or found_email
        self.version = version or found_version or ''
        self.usage = usage
        self.description = description
        self.epilog = epilog

    def _find_info(self):
        _stack = stack()
        top_level_frame_info = _stack[-1]
        installed_via_setup, g = self._find_dunder_info(top_level_frame_info)
        email, version, repo_url = g.get('__author_email__'), g.get('__version__'), g.get('__url__')

        path = Path(getsourcefile(top_level_frame_info[0]))
        if installed_via_setup and path.name.endswith('-script.py'):
            try:
                path = path.with_name(Path(sys.argv[0]).name)
            except IndexError:
                path = path.with_name(path.stem[:-7] + '.py')
        return email, version, repo_url, path

    def _find_dunder_info(self, top_level_frame_info):  # noqa
        g = top_level_frame_info.frame.f_globals
        installed_via_setup = 'load_entry_point' in g and 'main' not in g  # TODO: This may need to be tweaked
        for level in reversed(stack()[:-1]):
            g = level.frame.f_globals
            if any(k in g for k in ('__author_email__', '__version__', '__url__')):
                return installed_via_setup, g
        return installed_via_setup, g

    def _docs_url_from_repo_url(self, repo_url: Optional[str]):  # noqa
        if repo_url and repo_url.startswith('https://github.com'):
            from urllib.parse import urlparse

            try:
                user, repo = urlparse(repo_url).path[1:].split('/')
            except Exception:
                return None
            else:
                return f'https://{user}.github.io/{repo}/'
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


def camel_to_snake_case(text: str, delim: str = '_') -> str:
    return ''.join(f'{delim}{c}' if i and c.isupper() else c for i, c in enumerate(text)).lower()


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


def is_numeric(text: str) -> Bool:
    try:
        num_match = is_numeric._num_match
    except AttributeError:
        is_numeric._num_match = num_match = re.compile(r'^-\d+$|^-\d*\.\d+?$').match
    return num_match(text)
