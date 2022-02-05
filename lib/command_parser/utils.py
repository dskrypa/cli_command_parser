"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from inspect import stack, getsourcefile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union, Sequence, Optional, Type
from string import whitespace, printable

from .exceptions import ParameterDefinitionError

if TYPE_CHECKING:
    from .parameters import Parameter

Bool = Union[bool, Any]

_NotSet = object()


class Args:
    def __init__(self, args: Optional[Sequence[str]]):
        self.raw = sys.argv[1:] if args is None else args
        self.remaining = self.raw
        self._parsed = {}
        self._provided = defaultdict(int)

    def __repr__(self) -> str:
        provided = dict(self._provided)
        return f'<{self.__class__.__name__}[parsed={self._parsed}, remaining={self.remaining}, {provided=}]>'

    def record_action(self, param: 'Parameter', val_count: int = 1):
        self._provided[param] += val_count

    def num_provided(self, param: 'Parameter') -> int:
        return self._provided[param]

    def __getitem__(self, param: Union['Parameter', str]):
        try:
            return self._parsed[param]
        except KeyError:
            if isinstance(param, str):
                try:
                    return next((v for p, v in self._parsed.items() if p.name == param))
                except StopIteration:
                    raise KeyError(f'{param=} was not provided / parsed') from None
            else:
                self._parsed[param] = value = param._init_value_factory()
                return value

    def __setitem__(self, param: 'Parameter', value):
        self._parsed[param] = value

    def find_all(self, param_type: Type['Parameter']) -> dict['Parameter', Any]:
        return {param: val for param, val in self._parsed.items() if isinstance(param, param_type)}


def validate_positional(
    param_cls: str, value: str, prefix: str = 'name', exc: Type[Exception] = ParameterDefinitionError
):
    if not value or value.startswith('-'):
        raise exc(f"Invalid {param_cls} {prefix}={value!r} - may not be empty or start with '-'")
    elif bad := {c for c in value if (c in whitespace and c != ' ') or c not in printable}:
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
        installed_via_setup = 'load_entry_point' in g and 'main' not in g
        for level in reversed(stack[:-1]):
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
        if version := self.version:
            version = f' [ver. {version}]'
        if email := self.email:
            parts.append(f'Report {self.prog}{version} bugs to {email}')
        if url := self.docs_url or self.url:
            parts.append(f'Online documentation: {url}')
        return '\n\n'.join(parts)
