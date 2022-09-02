"""
Utilities for generating documentation for Commands

:author: Doug Skrypa
"""

from __future__ import annotations

import sys
from collections import defaultdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING, Type, Dict

from .commands import Command
from .context import get_current_context
from .core import CommandMeta, CommandType, get_params, get_parent
from .formatting.commands import get_formatter, NameFunc

if TYPE_CHECKING:
    from .typing import Bool, PathLike

__all__ = ['render_script_rst', 'render_command_rst', 'load_commands']

Commands = Dict[str, Type[Command]]


def render_script_rst(
    path: PathLike, top_only: Bool = True, fix_name: Bool = True, fix_name_func: NameFunc = None
) -> str:
    """Load all Commands from the file with the given path, and generate a single RST string based on those Commands"""
    commands = load_commands(path, top_only)
    return _render_commands_rst(commands, fix_name, fix_name_func)


def render_command_rst(command: CommandType, fix_name: Bool = True, fix_name_func: NameFunc = None) -> str:
    """
    :param command: The :class:`.Command` to document
    :param fix_name: Whether the file name should be re-formatted from CamelCase / snake_case to separate Title Case
      words or not (default: True)
    :param fix_name_func: The function to call if ``fix_name`` is True instead of the default one.
    :return: The help text for the given Command, formatted using RST
    """
    ctx = get_current_context(True) or command()._Command__ctx
    with ctx:
        return get_formatter(command).format_rst(fix_name, fix_name_func)


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
    module = import_module(path)
    commands = {key: val for key, val in module.__dict__.items() if not key.startswith('__') and _is_command(val)}
    return top_level_commands(commands) if top_only else commands


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
