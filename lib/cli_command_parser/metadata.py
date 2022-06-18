"""
Utilities for extracting types from annotations, finding / storing program metadata, and other misc utilities.

:author: Doug Skrypa
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from inspect import stack, FrameInfo
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional, Sequence, Tuple, Dict
from urllib.parse import urlparse

if TYPE_CHECKING:
    from .utils import Bool

__all__ = ['ProgramMetadata', 'ProgInfo']


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

    def _init(self, info: ProgInfo):
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

    def __repr__(self) -> str:
        attrs = (*self._cmd_args, 'usage', 'doc_str', 'path', 'epilog', 'description')
        part_iter = ((a, getattr(self, a)) for a in attrs)
        part_str = ', '.join(f'{a}={v!r}' for a, v in part_iter if v)
        return f'<{self.__class__.__name__}[{part_str}]>'

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
        except Exception:  # noqa  # pylint: disable=W0703
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
    def dynamic_import(cls, path: Path, module_globals: Dict[str, Any]):
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
        except Exception:  # noqa  # pylint: disable=W0703
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
