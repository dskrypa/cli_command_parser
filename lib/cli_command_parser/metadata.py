"""
Program metadata introspection for use in usage, help text, and documentation.

:author: Doug Skrypa
"""
# pylint: disable=R0801

from __future__ import annotations

from collections import defaultdict
from inspect import getmodule
from pathlib import Path
from sys import modules
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Type, Optional, Union, Tuple, Dict
from urllib.parse import urlparse

try:
    from importlib.metadata import entry_points, EntryPoint
except ImportError:  # Python 3.7
    from importlib_metadata import entry_points, EntryPoint

from .compat import cached_property
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
        owner._fields.add(name)

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
        if value is not None:
            instance.__dict__[self.name] = value

    def __repr__(self) -> str:
        return f'Metadata(default={self.default!r})'


class ProgramMetadata:
    _fields = {'parent'}
    parent: Optional[ProgramMetadata] = None
    path: Path = Metadata(None)
    package: str = Metadata(None)
    module: str = Metadata(None)
    command: str = Metadata(None)
    prog: str = Metadata(None)
    prog_src: str = Metadata(None)
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

    def __init__(self, **kwargs):
        fields = self._fields
        for key, val in kwargs.items():
            if key in fields:
                setattr(self, key, val)
            else:
                # The number of times one or more invalid options will be provided is extremely low compared to how
                # often this exception will not need to be raised, so the re-iteration over kwargs is acceptable.
                # This also avoids creating the `bad` dict that would otherwise be thrown away on 99.9% of init calls.
                bad = ', '.join(sorted(key for key in kwargs if key not in fields))
                raise TypeError(f'Invalid arguments for {self.__class__.__name__}: {bad}')

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

        prog, prog_src = _prog_finder.normalize(prog, path, parent, no_sys_argv, command)
        return cls(
            parent=parent,
            path=path,
            package=g.get('__package__'),
            module=g.get('__module__'),
            command=command.__qualname__,
            prog=prog,
            prog_src=prog_src,
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

    field_dict = {field: getattr(obj, field) for field in sorted(obj._fields)}
    prev_str = ' ' * indent
    indent += 4
    indent_str = ' ' * indent
    fields_str = '\n'.join(f'{indent_str}{k}={_repr(v, indent)},' for k, v in field_dict.items())
    return f'<{obj.__class__.__name__}(\n{fields_str}\n{prev_str})>'


class ProgFinder:
    @cached_property
    def mod_obj_prog_map(self) -> Dict[str, Dict[str, str]]:
        mod_obj_prog_map = defaultdict(dict)
        for entry_point in self._get_console_scripts():
            module, obj = map(str.strip, entry_point.value.split(':', 1))
            obj = obj.split('[', 1)[0].strip()  # Strip extras, if any
            mod_obj_prog_map[module][obj] = entry_point.name

        mod_obj_prog_map.default_factory = None  # Disable automatic defaults
        return mod_obj_prog_map

    @classmethod
    def _get_console_scripts(cls) -> Tuple[EntryPoint, ...]:
        try:
            return entry_points(group='console_scripts')
        except TypeError:  # Python 3.8 or 3.9
            return entry_points()['console_scripts']

    def normalize(
        self,
        prog: OptStr,
        cmd_path: Path,
        parent: Optional[ProgramMetadata],
        no_sys_argv: Bool,
        command: CommandType,
    ) -> Tuple[OptStr, str]:
        if prog:
            return prog, 'class kwargs'

        ep_name = self._from_entry_point(command)
        if ep_name:
            return ep_name, 'entry_points'

        if no_sys_argv is None:
            try:
                no_sys_argv = not ctx.allow_argv_prog
            except NoActiveContext:
                no_sys_argv = False

        # if parent and parent.prog != parent.path.name and (not no_sys_argv or not parent.prog_from_sys_argv):
        #     return parent.prog, parent.prog_from_sys_argv
        if parent and parent.prog != parent.path.name and (not no_sys_argv or parent.prog_src != 'sys.argv'):
            return parent.prog, parent.prog_src
        elif not no_sys_argv:
            argv_name = self._from_sys_argv()
            if argv_name:
                return argv_name, 'sys.argv'

        return cmd_path.name, 'path'

    def _from_entry_point(self, command: CommandType) -> OptStr:
        main_mod = 'cli_command_parser.commands'
        for prog, obj, obj_mod, obj_name in self._iter_entry_point_candidates(command):
            if obj is command or (obj_mod == main_mod and obj_name == 'main'):
                return prog

        return None

    def _iter_entry_point_candidates(self, command: CommandType):
        try:
            # TODO: This likely won't work for a base command in one module, sub commands defined in separate modules,
            #  and main imported from cli_command_parser in the package's __init__/__main__ module...
            obj_prog_map = self.mod_obj_prog_map[command.__module__]
            module = modules[command.__module__]
        except KeyError as e:
            pass
        else:
            for obj_name, prog in obj_prog_map.items():
                base_name = obj_name.split('.', 1)[0]
                try:
                    obj = getattr(module, base_name)
                except AttributeError:
                    pass
                else:
                    yield prog, obj, getattr(obj, '__module__', ''), getattr(obj, '__name__', '')

    def _from_sys_argv(self) -> OptStr:
        try:
            ctx_prog = ctx.prog
        except NoActiveContext:
            return None

        if ctx_prog:
            path = Path(ctx_prog)
            # Windows allows invocation without .exe - assume a file with an extension is a match
            if path.exists() or next(path.parent.glob(f'{path.name}.???'), None) is not None:
                return path.name

        return None


_prog_finder = ProgFinder()


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
