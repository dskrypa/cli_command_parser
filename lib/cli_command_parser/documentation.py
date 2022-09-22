"""
Utilities for generating documentation for Commands

:author: Doug Skrypa
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Mapping, List, Dict

from .commands import Command
from .context import Context
from .core import CommandMeta, get_params, get_parent, get_metadata
from .formatting.commands import get_formatter, NameFunc
from .formatting.restructured_text import MODULE_TEMPLATE, rst_header, rst_toc_tree

if TYPE_CHECKING:
    from .typing import Bool, PathLike, CommandCls, Strings

    Commands = Dict[str, CommandCls]

__all__ = ['render_script_rst', 'render_command_rst', 'load_commands', 'RstWriter']
log = logging.getLogger(__name__)


# region Render Script / Command RST


def render_script_rst(
    path: PathLike, top_only: Bool = True, fix_name: Bool = True, fix_name_func: NameFunc = None
) -> str:
    """Load all Commands from the file with the given path, and generate a single RST string based on those Commands"""
    commands = load_commands(path, top_only)
    return _render_commands_rst(commands, fix_name, fix_name_func)


def render_command_rst(command: CommandCls, fix_name: Bool = True, fix_name_func: NameFunc = None) -> str:
    """
    :param command: The :class:`.Command` to document
    :param fix_name: Whether the file name should be re-formatted from CamelCase / snake_case to separate Title Case
      words or not (default: True)
    :param fix_name_func: The function to call if ``fix_name`` is True instead of the default one.
    :return: The help text for the given Command, formatted using RST
    """
    with Context([], command, allow_argv_prog=False):
        return get_formatter(command).format_rst(fix_name, fix_name_func, no_sys_argv=True)


def _render_commands_rst(commands: Commands, fix_name: Bool = True, fix_name_func: NameFunc = None) -> str:
    # This could be better, but it's relatively unlikely to have multiple top level commands in a script...
    # For the same reason that main() does not try to pick one, this will just combine all of them.
    parts = []
    for i, (_name, command) in enumerate(sorted(commands.items())):
        if i:
            parts.append('\n--------\n')

        parts.append(render_command_rst(command, fix_name, fix_name_func))

    if len(parts) == 1:
        return parts[0]
    return '\n'.join(parts)


# endregion


# region Import and Load Commands


def load_commands(path: PathLike, top_only: Bool = False) -> Commands:
    """
    Load all of the commands from the file with the given path and return them as a dict of ``{name: Command}``.

    If an :class:`python:OSError` or a subclass thereof is encountered while attempting to load the file (due to the
    path not existing, or a permission error, etc), it will be allowed to propagate.  An :class:`python:ImportError`
    may be raised by :func:`import_module` if the specified path cannot be imported.

    :param path: The path to a file containing one or more :class:`.Command` classes
    :param top_only: If True, then only top-level commands are returned (default: all)
    :return: Dict containing the Commands loaded from the given file
    """
    with Context(allow_argv_prog=False):
        module = import_module(path)
    commands = {key: val for key, val in module.__dict__.items() if not key.startswith('__') and _is_command(val)}
    if top_only:
        commands = top_level_commands(commands)

    doc_str = module.__doc__
    if doc_str:
        for command in commands.values():
            get_metadata(command).pkg_doc_str = doc_str

    return commands


def top_level_commands(commands: Commands) -> Commands:
    """Filter the given commands to only the ones that do not have a parent present in the provided dict of commands"""
    if len(commands) <= 1:
        return commands

    indirect_parents = defaultdict(set)
    for name, command in commands.items():
        sub_command = get_params(command).sub_command
        if sub_command:
            for choice in sub_command.choices.values():
                indirect_parents[choice.target].add(command)

    all_commands = set(commands.values())

    filtered = {}
    for name, command in commands.items():
        parent = get_parent(command, False)
        if not ((parent and parent in all_commands) or indirect_parents[command]):
            filtered[name] = command

    return filtered


def import_module(path: PathLike):
    """Import the module / package from the given path"""
    path = Path(path)
    name = path.stem
    if path.is_dir():
        path /= '__init__.py'
    spec = spec_from_file_location(name, path)
    try:
        module = module_from_spec(spec)
    except AttributeError as e:
        path_str = path.as_posix()
        raise ImportError(f'Invalid path={path_str!r} - are you sure it is a Python module?', path=path_str) from e
    sys.modules[spec.name] = module  # This is required for the program metadata introspection
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[spec.name]
        raise
    return module


def _is_command(obj) -> bool:
    return isinstance(obj, CommandMeta) and obj is not Command


# endregion


class RstWriter:
    def __init__(
        self,
        output_dir: PathLike,
        *,
        dry_run: Bool = False,
        encoding: str = 'utf-8',
        newline: str = '\n',
        ext: str = '.rst',
        module_template: str = MODULE_TEMPLATE,
        skip_modules: Strings = None,
    ):
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.encoding = encoding
        self.newline = newline
        self.ext = ext
        self.module_template = module_template
        self.skip_modules = set(skip_modules) if skip_modules else set()

    def document_script(
        self,
        path: Path,
        subdir: str = None,
        name: str = None,
        replacements: Mapping[str, str] = None,
        top_only: Bool = True,
        **kwargs,
    ) -> str:
        if name:
            kwargs['fix_name_func'] = lambda n: name
            rst_name = Path(name).stem
        else:
            rst_name = path.stem

        rst_str = render_script_rst(path, top_only=top_only, **kwargs)
        if replacements:
            for key, val in replacements.items():
                rst_str = rst_str.replace(key, val)

        self.write_rst(rst_name, rst_str, subdir)
        return rst_name

    def document_scripts(
        self,
        paths: Iterable[Path],
        subdir: str = None,
        top_only: Bool = True,
        *,
        index_name: str = None,
        index_header: str = None,
        index_subdir: str = None,
        caption: str = None,
        **kwargs,
    ):
        names = [self.document_script(path, subdir, top_only=top_only, **kwargs) for path in paths]
        if index_name or index_header or index_subdir:
            name = index_name or subdir
            self.write_index(name, index_header or name.title(), names, subdir, caption, index_subdir)

    def document_module(self, module: str, subdir: str = None):
        name = module.split('.')[-1].title()
        rendered = MODULE_TEMPLATE.format(header=rst_header(f'{name} Module', 2), module=module)
        self.write_rst(module, rendered, subdir)

    def document_package(
        self,
        pkg_name: str,
        pkg_path: Path,
        subdir: str = None,
        *,
        name: str = None,
        header: str = None,
        index: Bool = True,
        empty: Bool = False,
        caption: str = None,
    ) -> List[str]:
        """
        :param pkg_name: The name of the package to document
        :param pkg_path: The path to the package
        :param subdir: The output subdirectory for package contents
        :param name: The name to use for the index file
        :param header: Header text to use in the index (default is based on the package name)
        :param index: Whether the index file should be created
        :param empty: Whether an index file should be created if the package had no modules to document
        :param caption: A caption to use for the index
        :return: List of the names from the contents of the package
        """
        if name:
            index_subdir = content_subdir = f'{subdir}/{name}' if subdir else name
        else:
            index_subdir = None
            content_subdir = subdir

        contents = self._generate_code_rsts(pkg_name, pkg_path, content_subdir)
        if (not contents and not empty) or not index:
            return contents

        if not header:
            header = '{} Package'.format(pkg_name.split('.')[-1].title())

        self.write_index(name or pkg_name, header, contents, index_subdir, caption=caption, subdir=subdir)
        return contents

    def _generate_code_rsts(self, pkg_name: str, pkg_path: Path, subdir: str = None) -> List[str]:
        contents = []
        for path in pkg_path.iterdir():
            if path.is_dir():
                sub_pkg_name = f'{pkg_name}.{path.name}'
                pkg_modules = self.document_package(sub_pkg_name, path, subdir)
                if pkg_modules:
                    contents.append(sub_pkg_name)
            elif path.is_file() and path.suffix == '.py' and not path.name.startswith('__'):
                name = f'{pkg_name}.{path.stem}'
                if name in self.skip_modules:
                    continue
                contents.append(name)
                self.document_module(name, subdir)

        return contents

    def write_index(
        self,
        name: str,
        header: str,
        contents: Strings,
        content_subdir: str = None,
        caption: str = None,
        subdir: str = None,
    ):
        content_fmt = '    {}' if content_subdir is None else f'    {content_subdir}/{{}}'
        rendered = rst_toc_tree(header, content_fmt, contents, caption=caption)
        self.write_rst(name, rendered, subdir)

    def write_rst(self, name: str, content: str, subdir: str = None):
        target_dir = self.output_dir.joinpath(subdir) if subdir else self.output_dir
        if not self.dry_run and not target_dir.exists():
            target_dir.mkdir(parents=True)

        prefix = '[DRY RUN] Would write' if self.dry_run else 'Writing'
        path = target_dir.joinpath(name + self.ext)
        log.debug(f'{prefix} {path.as_posix()}')
        if not self.dry_run:
            # Path.write_text on 3.7 does not support `newline`
            with path.open('w', encoding=self.encoding, newline=self.newline) as f:
                f.write(content)
