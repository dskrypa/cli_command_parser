"""
Core classes / functions for Commands, including the metaclass used for Commands, and utilities for finding the primary
top-level Command.

:author: Doug Skrypa
"""

from __future__ import annotations

from abc import ABC, ABCMeta
from typing import TYPE_CHECKING, Optional, Union, TypeVar, Type, Any, Dict, Tuple, List
from warnings import warn
from weakref import WeakKeyDictionary, WeakSet

from .actions import help_action
from .command_parameters import CommandParameters
from .config import CommandConfig
from .exceptions import CommandDefinitionError
from .utils import ProgramMetadata

if TYPE_CHECKING:
    from .commands import Command

Bases = Tuple[type, ...]
Config = Optional[CommandConfig]
AnyConfig = Union[Config, Dict[str, Any]]


class CommandMeta(ABCMeta, type):
    # noinspection PyUnresolvedReferences
    """
    :param choice: SubCommand value that maps to this command
    :param prog: The name of the program (default: ``sys.argv[0]``)
    :param usage: Usage message (default: auto-generated)
    :param description: Description of what the program does
    :param epilog: Text to follow parameter descriptions
    :param help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
    :param doc_name: Name to use in documentation (default: the stem of the file name containing the Command, or
      the specified ``prog`` value)
    :param error_handler: The :class:`~.error_handling.ErrorHandler` to be used by
      :meth:`Command.__call__<.commands.Command.__call__>` to wrap :meth:`~.commands.Command.main`, or None to
      disable error handling.
    :param bool add_help: Whether the --help / -h action_flag should be added
    :param bool action_after_action_flags: Whether action_flag methods are allowed to be combined with a positional
      Action method in a given CLI invocation
    :param bool multiple_action_flags: Whether multiple action_flag methods are allowed to run if they are all
      specified
    :param bool ignore_unknown: Whether unknown arguments should be allowed (default: raise an exception when
      unknown arguments are encountered)
    :param bool allow_missing: Whether missing required arguments should be allowed (default: raise an exception
      when required arguments are missing)
    :param bool always_run_after_main: Whether :meth:`Command._after_main_` should always be called, even if an
      exception was raised in :meth:`Command.main`
    """

    _tmp_configs = {}
    _configs = WeakKeyDictionary()
    _params = WeakKeyDictionary()
    _metadata = WeakKeyDictionary()
    _commands = WeakSet()

    def __new__(
        mcs,
        name: str,
        bases: Bases,
        namespace: Dict[str, Any],
        *,
        choice: str = None,
        help: str = None,  # noqa
        config: AnyConfig = None,
        **kwargs,
    ):
        metadata = {k: kwargs.pop(k, None) for k in ('prog', 'usage', 'description', 'epilog', 'doc_name')}
        with _PrepConfig(mcs, namespace, mcs._prepare_config(bases, config, kwargs)) as cfg_prep:
            cfg_prep.cls = cls = super().__new__(mcs, name, bases, namespace)

        mcs._commands.add(cls)
        mcs._maybe_populate_metadata(cls, **metadata)
        mcs._maybe_register_sub_cmd(cls, choice, help)

        config = mcs.config(cls)
        if config is not None and config.add_help and not hasattr(cls, '_CommandMeta__help'):
            cls.__help = help_action  # pylint: disable=W0238

        return cls

    @classmethod
    def _maybe_populate_metadata(
        mcs,
        cls,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        doc_name: str = None,
    ):
        """Maybe populate ProgramMetadata for this class; inherit from parent when possible"""
        meta = mcs.meta(cls)
        doc = None if cls.__module__ == 'cli_command_parser.commands' else cls.__doc__
        if meta is not None and not any((prog, usage, description, epilog, doc_name, doc)):
            return
        mcs._metadata[cls] = ProgramMetadata(
            prog=prog, usage=usage, description=description, epilog=epilog, doc_name=doc_name, doc=doc
        )

    @classmethod
    def _maybe_register_sub_cmd(mcs, cls, choice: str = None, help: str = None):  # noqa
        parent = mcs.parent(cls, False)
        if parent:
            sub_cmd = mcs.params(parent).sub_command
            if sub_cmd is not None:
                sub_cmd.register_command(choice, cls, help)
            elif choice:
                warn(
                    f'choice={choice!r} was not registered for {cls} because'
                    f' its parent={parent!r} has no SubCommand parameter'
                )
        elif choice:
            warn(f'choice={choice!r} was not registered for {cls} because it has no parent Command')

    @classmethod
    def parent(mcs, cls: CommandMeta, include_abc: bool = True) -> Optional[CommandMeta]:
        for parent_cls in type.mro(cls)[1:]:
            if isinstance(parent_cls, CommandMeta) and (include_abc or ABC not in parent_cls.__bases__):
                return parent_cls
        return None

    @classmethod
    def _config_from_bases(mcs, bases: Bases) -> Config:
        for base in bases:
            if isinstance(base, mcs):
                return mcs.config(base)
        return None

    @classmethod
    def _prepare_config(mcs, bases: Bases, config: AnyConfig, kwargs: Dict[str, Any]):
        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine config={config!r} with keyword config arguments={kwargs}')
            if not isinstance(config, CommandConfig):
                config = CommandConfig(**config)
            return config
        else:
            config = mcs._config_from_bases(bases)
            if kwargs or (config is None and ABC not in bases):
                if config is not None:
                    # kwargs = config.as_dict() | kwargs
                    for key, val in config.as_dict().items():  # py < 3.9 compatibility
                        kwargs.setdefault(key, val)

                return CommandConfig(**kwargs)

        return None

    @classmethod
    def config(mcs, cls: CommandMeta) -> Config:
        try:
            return mcs._configs[cls]
        except KeyError:
            pass
        try:
            return mcs._tmp_configs[f'{cls.__module__}.{cls.__qualname__}']
        except KeyError:
            pass
        parent = mcs.parent(cls)
        if parent is not None:
            return mcs.config(parent)
        return None

    @classmethod
    def params(mcs, cls: CommandMeta) -> CommandParameters:
        try:
            return mcs._params[cls]
        except KeyError:
            parent = mcs.parent(cls, False)
            mcs._params[cls] = params = CommandParameters(cls, parent)
            return params

    @classmethod
    def meta(mcs, cls: CommandMeta) -> Optional[ProgramMetadata]:
        try:
            return mcs._metadata[cls]
        except KeyError:
            parent = mcs.parent(cls)
            if parent is not None:
                return mcs.meta(parent)
            return None


class _PrepConfig:
    """
    Temporarily stores config with a str key because __set_name__ for Parameters is called when super().__new__ is
    called to create the Command class, and some config needs to be known at that point.
    """

    __slots__ = ('mcs', 'config_key', 'config', 'cls')

    def __init__(self, mcs: Type[CommandMeta], ns: Dict[str, Any], config: Config):
        self.mcs = mcs
        self.config_key = '{__module__}.{__qualname__}'.format(**ns)
        self.config = config

    def __enter__(self) -> _PrepConfig:
        if self.config is not None:
            self.mcs._tmp_configs[self.config_key] = self.config
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.mcs._configs[self.cls] = self.mcs._tmp_configs.pop(self.config_key)
        except (KeyError, AttributeError):
            pass


def get_parent(command: Union[CommandMeta, Command], include_abc: bool = True) -> Optional[CommandMeta]:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.parent(command, include_abc)


def get_config(command: Union[CommandMeta, Command]) -> CommandConfig:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.config(command)


def get_params(command: Union[CommandMeta, Command]) -> CommandParameters:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.params(command)


def get_top_level_commands() -> List[Union[CommandMeta, Type[Command]]]:
    """
    Returns a list of Command subclasses that are inferred to be direct subclasses of :class:`~commands.Command`.

    This was implemented because ``Command.__subclasses__()`` does not release dead references to subclasses quickly
    enough for tests.
    """
    return [cmd for cmd in CommandMeta._commands if sum(isinstance(cls, CommandMeta) for cls in cmd.mro()) == 2]


CommandType = TypeVar('CommandType', bound=CommandMeta)  # pylint: disable=C0103
