"""
Program metadata introspection for use in usage, help text, and documentation.

:author: Doug Skrypa
"""
# pylint: disable=R0801

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from importlib.metadata import Distribution, EntryPoint, entry_points
from inspect import getmodule
from pathlib import Path
from sys import modules
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Type, Union
from urllib.parse import urlparse

from .context import NoActiveContext, ctx

if TYPE_CHECKING:
    from .typing import Bool, CommandType, OptStr

__all__ = ['ProgramMetadata']

DEFAULT_FILE_NAME: str = 'UNKNOWN'


# region Metadata Descriptors


class MetadataBase:
    __slots__ = ('name', 'inheritable')

    def __init__(self, inheritable: bool = True):
        self.inheritable = inheritable

    def __set_name__(self, owner: Type[ProgramMetadata], name: str):
        self.name = name
        owner._fields.add(name)

    def __get__(self, instance: Optional[ProgramMetadata], owner: Type[ProgramMetadata]):
        try:
            return instance.__dict__[self.name]
        except AttributeError:  # instance is None
            return self
        except KeyError:
            pass
        if self.inheritable and (parent := self.get_parent(instance)):
            return getattr(parent, self.name)
        return self.get_value(instance)

    def __set__(self, instance: ProgramMetadata, value: Union[str, Path, None]):
        if value is not None:
            instance.__dict__[self.name] = value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(f"{a}={v}" for a, v in self._attrs())})'

    def _attrs(self) -> Iterator[tuple[str, Any]]:
        for base in self.__class__.mro()[:-1]:
            for attr in base.__slots__:  # noqa
                if attr != 'name':
                    value = getattr(self, attr)
                    yield attr, (getattr(value, '__qualname__', value) if attr == 'func' else repr(value))

    def get_parent(self, instance: ProgramMetadata) -> Optional[ProgramMetadata]:
        # if (parent := instance.parent) and parent.distribution == instance.distribution:
        if (parent := instance.parent) and parent.package == instance.package:
            return parent
        return None

    def get_value(self, instance: ProgramMetadata):
        raise NotImplementedError


class Metadata(MetadataBase):
    __slots__ = ('default',)

    def __init__(self, default, inheritable: bool = True):
        super().__init__(inheritable)
        self.default = default

    def get_value(self, instance: ProgramMetadata):
        return self.default


class DynamicMetadata(MetadataBase):
    __slots__ = ('func',)

    def __init__(self, func: Callable[[ProgramMetadata], Any], inheritable: bool = True):
        super().__init__(inheritable)
        self.func = func

    def get_value(self, instance: ProgramMetadata):
        instance.__dict__[self.name] = result = self.func(instance)
        return result


def dynamic_metadata(func=None, *, inheritable: bool = True):
    if func is None:
        return lambda f: DynamicMetadata(f, inheritable)
    else:
        return DynamicMetadata(func, inheritable)


# endregion


class ProgramMetadata:
    _fields = {'parent'}
    parent: Optional[ProgramMetadata] = None
    distribution: Distribution | None = Metadata(None, inheritable=False)
    path: Path = Metadata(None, inheritable=False)
    package: str = Metadata(None, inheritable=False)
    module: str = Metadata(None, inheritable=False)
    cmd_module: str = Metadata(None, inheritable=False)
    command: str = Metadata(None, inheritable=False)
    usage: str = Metadata(None)
    description: str = Metadata(None)
    epilog: str = Metadata(None)
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
    ) -> ProgramMetadata:
        path, g = _path_and_globals(command, path)
        if command.__module__ != 'cli_command_parser.commands':
            # Prevent inheritors from getting docstrings from the base Command
            doc_str = g.get('__doc__')
            doc = command.__doc__
        else:
            doc = doc_str = None

        return cls(
            parent=parent,
            distribution=_dist_finder.dist_for_obj(command),
            path=path,
            package=g.get('__package__'),
            module=g.get('__module__'),
            cmd_module=command.__module__,
            command=command.__qualname__,
            prog=prog,
            url=url or g.get('__url__'),
            docs_url=docs_url,
            email=email or g.get('__author_email__'),
            version=version or g.get('__version__'),
            usage=usage,
            description=_description(description, doc),
            epilog=epilog,
            doc_name=doc_name,
            doc_str=doc_str,
        )

    def __repr__(self) -> str:
        return _repr(self)

    # region Program Name Properties

    @cached_property
    def _prog_and_src(self) -> tuple[str, str]:
        if prog := self.__dict__.get('prog'):
            return prog, 'class kwargs'
        return _prog_finder.normalize(self.path, self.parent, None, self.cmd_module, self.command)

    @dynamic_metadata
    def prog(self) -> str:
        return self._prog_and_src[0]

    @cached_property
    def _doc_prog_and_src(self) -> tuple[str, str]:
        if prog := self.__dict__.get('prog'):
            return prog, 'class kwargs'
        return _prog_finder.normalize(self.path, self.parent, False, self.cmd_module, self.command)

    def get_prog(self, allow_sys_argv: Bool = None) -> str:
        return self._get_prog(allow_sys_argv)[0]

    def _get_prog(self, allow_sys_argv: Bool = None) -> tuple[str, str]:
        return self._prog_and_src if allow_sys_argv or allow_sys_argv is None else self._doc_prog_and_src

    @dynamic_metadata(inheritable=False)
    def doc_name(self) -> str:
        # TODO: Bug: Explicitly provided value not used in rst page title sometimes?
        return Path(self._doc_prog_and_src[0]).stem

    # endregion

    @dynamic_metadata
    def version(self) -> str:
        if dist := self.distribution:
            return dist.version
        return ''

    @dynamic_metadata
    def email(self) -> OptStr:
        if dist := self.distribution:
            if email := dist.metadata['Author-email']:
                # TODO: `Maintainer-email` instead if it's defined?  Is there a more appropriate key?
                # https://packaging.python.org/en/latest/specifications/core-metadata/#core-metadata
                return email
        return None

    @dynamic_metadata
    def url(self) -> OptStr:
        if (dist := self.distribution) and (urls := _dist_finder.get_urls(dist)):
            for key in ('Source', 'Source Code', 'Home-page'):
                if url := urls.get(key):
                    return url
        return None

    @dynamic_metadata
    def docs_url(self) -> OptStr:
        if (dist := self.distribution) and (urls := _dist_finder.get_urls(dist)):
            for key in ('Documentation', 'Docs', 'Doc', 'Home-page'):
                if url := urls.get(key):
                    return url
        return _docs_url_from_repo_url(self.url)  # noqa

    def format_epilog(self, extended: Bool = True, allow_sys_argv: Bool = None) -> str:
        parts = [self.epilog] if self.epilog else []
        if parts and not extended:
            return parts[0]

        if version := self.version:
            version = f' [ver. {version}]'
        if self.email:
            parts.append(f'Report {self.get_prog(allow_sys_argv)}{version} bugs to {self.email}')
        if url := self.docs_url or self.url:
            parts.append(f'Online documentation: {url}')
        return '\n\n'.join(parts)

    def get_doc_str(self, strip: Bool = True) -> OptStr:
        if (doc_str := self.pkg_doc_str) and strip:
            doc_str = doc_str.strip()
        if not doc_str:
            if (doc_str := self.doc_str) and strip:
                doc_str = doc_str.strip()
        return doc_str

    def get_description(self, allow_inherited: Bool = True) -> OptStr:
        if description := self.description:
            if not allow_inherited and (parent := self.parent) and (parent_description := parent.description):  # noqa
                return description if parent_description != description else None
        return description


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
    def mod_obj_prog_map(self) -> dict[str, dict[str, str]]:
        mod_obj_prog_map = defaultdict(dict)
        for entry_point in self._get_console_scripts():
            module, obj = map(str.strip, entry_point.value.split(':', 1))
            obj = obj.split('[', 1)[0].strip()  # Strip extras, if any
            mod_obj_prog_map[module][obj] = entry_point.name

        mod_obj_prog_map.default_factory = None  # Disable automatic defaults
        return mod_obj_prog_map

    @classmethod
    def _get_console_scripts(cls) -> tuple[EntryPoint, ...]:
        try:
            return entry_points(group='console_scripts')  # noqa
        except TypeError:  # Python 3.8 or 3.9
            return entry_points()['console_scripts']  # noqa

    def normalize(
        self,
        cmd_path: Path,
        parent: Optional[ProgramMetadata],
        allow_sys_argv: Bool,
        cmd_module: str,
        cmd_name: str,
    ) -> tuple[OptStr, str]:
        if ep_name := self._from_entry_point(cmd_module, cmd_name):
            return ep_name, 'entry_points'

        if allow_sys_argv is None:
            try:
                allow_sys_argv = ctx.allow_argv_prog
            except NoActiveContext:
                allow_sys_argv = True

        if parent:
            p_prog, p_src = parent._get_prog(allow_sys_argv)
            if p_prog and p_src != 'path':
                return p_prog, p_src

        if allow_sys_argv and (argv_name := self._from_sys_argv()):
            return argv_name, 'sys.argv'

        return cmd_path.name, 'path'

    def _from_entry_point(self, cmd_module: str, cmd_name: str) -> OptStr:
        # TODO: Verify whether this is working for documentation generation...
        main_mod = 'cli_command_parser.commands'
        for prog, obj, obj_mod, obj_name in self._iter_entry_point_candidates(cmd_module):
            if (obj_name == cmd_name and obj_mod == cmd_module) or (obj_mod == main_mod and obj_name == 'main'):
                return prog

        return None

    def _iter_entry_point_candidates(self, cmd_module: str):
        # TODO: Use ProgramMetadata.distribution.entry_points() instead?
        try:
            # TODO: This likely won't work for a base command in one module, sub commands defined in separate modules,
            #  and main imported from cli_command_parser in the package's __init__/__main__ module...
            obj_prog_map = self.mod_obj_prog_map[cmd_module]
            module = modules[cmd_module]
        except KeyError:
            pass
        else:
            for obj_name, prog in obj_prog_map.items():
                base_name = obj_name.split('.', 1)[0]
                try:
                    obj = getattr(module, base_name)
                except AttributeError:
                    pass
                else:
                    yield prog, obj, getattr(obj, '__module__', ''), getattr(obj, '__qualname__', '')

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


class DistributionFinder:
    def __init__(self):
        self._dist_top_levels = {}
        self._dist_urls = {}

    @cached_property
    def _distributions(self) -> dict[str, Distribution]:
        # Note: Distribution.name was not added until 3.10, and it returns `self.metadata['Name']`
        return {dist.metadata['Name']: dist for dist in Distribution.discover()}

    def _get_top_levels(self, dist_name: str, dist: Distribution) -> set[str]:
        # dist_name = dist.metadata['Name']  # Distribution.name was not added until 3.10, and it returns this
        if (top_levels := self._dist_top_levels.get(dist_name)) is not None:
            return top_levels
        elif raw := dist.read_text('top_level.txt'):
            self._dist_top_levels[dist_name] = top_levels = {pkg for pkg in map(str.strip, raw.split()) if pkg}
            return top_levels

        # Below logic is copied from importlib.metadata._top_level_inferred from 3.10+
        self._dist_top_levels[dist_name] = inferred = {
            f.parts[0] if len(f.parts) > 1 else f.with_suffix('').name for f in dist.files if f.suffix == '.py'
        }
        return inferred

    def dist_for_pkg(self, pkg_name: str) -> Distribution | None:
        for dist_name, dist in self._distributions.items():
            if pkg_name in self._get_top_levels(dist_name, dist):
                return dist
        return None

    def dist_for_obj(self, obj) -> Distribution | None:
        try:
            mod_name: str = obj.__module__
        except AttributeError:
            return None

        if mod_name == '__main__':  # May need to handle __mp_main__ and similar too
            return self._dist_for_obj_main(obj)
        return self.dist_for_pkg(mod_name.split('.', 1)[0])

    def _dist_for_obj_main(self, obj) -> Distribution | None:
        # Note: getmodule returns the module object (obj.__module__ only provides the name)
        if (module := getmodule(obj)) is None or not module.__package__:
            return None

        # The package name may have a prefix like `lib` not included in top_level when interactive
        for part in module.__package__.split('.'):
            if (dist := self.dist_for_pkg(part)) is not None:
                return dist
        return None

    def get_urls(self, dist: Distribution) -> dict[str, str]:
        metadata = dist.metadata
        dist_name = metadata['Name']
        if (urls := self._dist_urls.get(dist_name)) is not None:
            return urls

        urls = {}
        for key, val in metadata.items():
            if key == 'Home-page':
                urls[key] = val
            elif key == 'Project-URL':
                url_type, url = val.split(',', 1)
                urls[url_type.strip()] = url.strip()
        self._dist_urls[dist_name] = urls
        return urls


_dist_finder = DistributionFinder()


def _path_and_globals(command: CommandType, path: Path = None) -> tuple[Path, dict[str, Any]]:
    module = getmodule(command)  # Returns the module object (obj.__module__ just provides the name of the module)
    if path is None:
        try:
            path = Path(module.__file__).resolve()
        except AttributeError:  # module is None
            path = Path.cwd().joinpath(DEFAULT_FILE_NAME)

    if module is None:
        return path, {}

    return path, module.__dict__


def _description(description: OptStr, doc: OptStr) -> OptStr:
    if description:
        return description
    elif doc:
        doc = dedent(doc).lstrip()
        if doc.strip():  # avoid space-only doc, but let possibly intentional trailing spaces / newlines to persist
            return doc
    return None


def _docs_url_from_repo_url(repo_url: OptStr) -> OptStr:
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
