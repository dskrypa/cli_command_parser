"""
Utilities for generating documentation for Commands

:author: Doug Skrypa
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Union, Type, Callable, Dict

from .commands import Command
from .context import get_current_context
from .core import CommandMeta, CommandType
from .formatting.commands import get_formatter
from .utils import ProgInfo, ProgramMetadata

__all__ = ['load_commands', 'get_rst']


def load_commands(path: Union[str, Path]) -> Dict[str, Type[Command]]:
    """
    :param path: The path to a file containing one or more :class:`.Command` classes
    :return: List of Commands loaded from the given file
    """
    module = load_module(path)
    commands = {key: val for key, val in module.__dict__.items() if not key.startswith('__') and is_command(val)}
    # Fix provenance metadata
    with ProgInfo._dynamic_import(Path(path), module.__dict__):
        for name, cmd_cls in commands.items():
            try:
                meta: ProgramMetadata = CommandMeta._metadata[cmd_cls]
            except KeyError:
                CommandMeta._metadata[cmd_cls] = ProgramMetadata()
            else:
                meta._init(ProgInfo())

    return commands


def get_rst(command: CommandType, fix_name: bool = True, fix_name_func: Callable[[str], str] = None) -> str:
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


def load_module(path: Union[str, Path]):
    path = Path(path)
    spec = spec_from_file_location(path.stem, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_command(obj) -> bool:
    try:
        return isinstance(obj, CommandMeta) and obj is not Command
    except TypeError:
        return False
