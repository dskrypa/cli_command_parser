"""
Program metadata introspection for use in usage, help text, and documentation.

:author: Doug Skrypa
"""
# pylint: disable=R0801

from __future__ import annotations

from dataclasses import dataclass, fields
from inspect import getmodule
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Type, Optional, Union, Tuple, Dict
from urllib.parse import urlparse

from .context import ctx, NoActiveContext

if TYPE_CHECKING:
    from .typing import Bool, CommandType, OptStr

__all__ = ['ProgramMetadata']

DEFAULT_FILE_NAME: str = 'UNKNOWN'


class Metadata:
    __slots__ = ('default', 'name')

    def __init__(self, default):
        self.default = default

    def __set_name__(self, owner: Type[ProgramMetadata], name: str):
        self.name = name

    def __get__(self, instance: Optional[ProgramMetadata], owner: Type[ProgramMetadata]):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.name]
        except KeyError:
            pass
        try:
            return getattr(instance.parent, self.name)
        except AttributeError:  # parent is None
            return self.default

    def __set__(self, instance: ProgramMetadata, value: Union[str, Path, None]):
        # Workaround for initial setting via dataclass + don't store None
        if not isinstance(value, Metadata) and value is not None:
            instance.__dict__[self.name] = value

    def __repr__(self) -> str:
        return f'Metadata(default={self.default!r})'


@dataclass
class ProgramMetadata:
    parent: Optional[ProgramMetadata] = None
    path: Path = Metadata(None)
    package: str = Metadata(None)
    module: str = Metadata(None)
    command: str = Metadata(None)
    prog: str = Metadata(None)
    prog_from_sys_argv: bool = Metadata(None)
    url: str = Metadata(None)
    docs_url: str = Metadata(None)
    email: str = Metadata(None)
    version: str = Metadata('')
    usage: str = Metadata(None)
    description: str = Metadata(None)
    epilog: str = Metadata(None)
    doc_name: str = Metadata(None)
    doc_str: str = Metadata('')
    pkg_doc_str: str = Metadata('')  # Set by :func:`~.documentation.load_commands` to capture package docstrings

    @classmethod
    def for_command(  # pylint: disable=R0914
        cls,
        command: CommandType,
        *,
        parent: ProgramMetadata = None,
        path: Path = None,
        prog: str = None,
        url: str = None,
        docs_url: str = None,
        email: str = None,
        version: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        doc_name: str = None,
        no_sys_argv: Bool = None,
    ) -> ProgramMetadata:
        path, g = _path_and_globals(command, path)
        if command.__module__ != 'cli_command_parser.commands':
            # Prevent inheritors from getting docstrings from the base Command
            doc_str = g.get('__doc__')
            doc = command.__doc__
        else:
            doc = doc_str = None

        prog, prog_from_sys_argv = _prog(prog, path, parent, no_sys_argv)
        return cls(
            parent=parent,
            path=path,
            package=g.get('__package__'),
            module=g.get('__module__'),
            command=command.__qualname__,
            prog=prog,
            prog_from_sys_argv=prog_from_sys_argv,
            url=url or g.get('__url__'),
            docs_url=docs_url or _docs_url_from_repo_url(url) or _docs_url_from_repo_url(g.get('__url__')),
            email=email or g.get('__author_email__'),
            version=version or g.get('__version__'),
            usage=usage,
            description=_description(description, doc),
            epilog=epilog,
            doc_name=_doc_name(doc_name, path, prog),
            doc_str=doc_str,
        )

    def __repr__(self) -> str:
        return _repr(self)

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

    def get_doc_str(self, strip: bool = True) -> OptStr:
        doc_str = self.pkg_doc_str
        if doc_str and strip:
            doc_str = doc_str.strip()
        if not doc_str:
            doc_str = self.doc_str
            if doc_str and strip:
                doc_str = doc_str.strip()
        return doc_str


def _repr(obj, indent=0) -> str:
    if not isinstance(obj, ProgramMetadata):
        return repr(obj)

    field_dict = {field.name: getattr(obj, field.name) for field in fields(obj)}
    prev_str = ' ' * indent
    indent += 4
    indent_str = ' ' * indent
    fields_str = '\n'.join(f'{indent_str}{k}={_repr(v, indent)},' for k, v in field_dict.items())
    return f'<{obj.__class__.__name__}(\n{fields_str}\n{prev_str})>'


def _prog(prog: OptStr, cmd_path: Path, parent: Optional[ProgramMetadata], no_sys_argv: Bool) -> Tuple[OptStr, bool]:
    # TODO: Attempt to detect the name to use via importlib.metadata.entry_points?  3.8+, with return value changes
    #  after 3.9
    if prog:
        return prog, False
    if no_sys_argv is None:
        try:
            no_sys_argv = not ctx.allow_argv_prog
        except NoActiveContext:
            no_sys_argv = False

    if parent and parent.prog != parent.path.name and (not no_sys_argv or not parent.prog_from_sys_argv):
        return parent.prog, parent.prog_from_sys_argv
    elif not no_sys_argv:
        try:
            ctx_prog = ctx.prog
        except NoActiveContext:
            ctx_prog = None

        if ctx_prog:
            path = Path(ctx_prog)
            # Windows allows invocation without .exe - assume a file with an extension is a match
            if path.exists() or next(path.parent.glob(f'{path.name}.???'), None) is not None:
                return path.name, True

    return cmd_path.name, False


def _path_and_globals(command: CommandType, path: Path = None) -> Tuple[Path, Dict[str, Any]]:
    module = getmodule(command)
    if path is None:
        try:
            path = Path(module.__file__).resolve()
        except AttributeError:  # module is None
            path = Path.cwd().joinpath(DEFAULT_FILE_NAME)

    if module is None:
        return path, {}

    return path, module.__dict__


def _description(description: Optional[str], doc: Optional[str]) -> Optional[str]:
    if description:
        return description
    elif doc:
        doc = dedent(doc).lstrip()
        if doc.strip():  # avoid space-only doc, but let possibly intentional trailing spaces / newlines to persist
            return doc
    return None


def _docs_url_from_repo_url(repo_url: Optional[str]) -> Optional[str]:
    if not repo_url:
        return None

    parsed = urlparse(repo_url)
    if parsed.scheme == 'https' and parsed.hostname == 'github.com':
        try:
            user, repo = parsed.path[1:].split('/', 1)
        except ValueError:
            pass
        else:
            return f'https://{user}.github.io/{repo}/'

    return None


def _doc_name(doc_name: Optional[str], path: Path, prog: str) -> str:
    if doc_name:
        return doc_name
    return Path(prog).stem
