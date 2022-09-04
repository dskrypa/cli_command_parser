"""
Core classes / functions for Commands, including the metaclass used for Commands, and utilities for finding the primary
top-level Command.

:author: Doug Skrypa
"""

from __future__ import annotations

from abc import ABC, ABCMeta
from typing import TYPE_CHECKING, Optional, Union, TypeVar, Callable, Iterable, Collection, Any, Dict, Tuple, List
from warnings import warn
from weakref import WeakSet

from .command_parameters import CommandParameters
from .config import CommandConfig
from .exceptions import CommandDefinitionError
from .metadata import ProgramMetadata

if TYPE_CHECKING:
    from .typing import Config, AnyConfig, CommandCls, CommandAny

__all__ = ['CommandMeta', 'get_parent', 'get_config', 'get_params', 'get_top_level_commands']

Bases = Union[Tuple[type, ...], Iterable[type]]
T = TypeVar('T')


class CommandMeta(ABCMeta, type):
    # noinspection PyUnresolvedReferences
    """
    :param choice: SubCommand value to map to this command.
    :param choices: SubCommand values to map to this command.
    :param prog: The name of the program (default: ``sys.argv[0]`` or the name of the module in which the top-level
      Command was defined in some cases)
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

    _commands = WeakSet()

    def __new__(
        mcs,
        name: str,
        bases: Bases,
        namespace: Dict[str, Any],
        *,
        choice: str = None,
        choices: Collection[str] = None,
        help: str = None,  # noqa
        config: AnyConfig = None,
        **kwargs,
    ) -> CommandCls:
        meta_iter = ((k, kwargs.pop(k, None)) for k in ('prog', 'usage', 'description', 'epilog', 'doc_name'))
        metadata = {k: v for k, v in meta_iter if v}
        namespace['_CommandMeta__params'] = None  # Prevent commands from inheriting parent params
        namespace['_CommandMeta__metadata'] = None  # Prevent commands from inheriting parent metadata directly
        config = mcs._prepare_config(bases, config, kwargs)
        if config:
            namespace['_CommandMeta__config'] = config

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        mcs._commands.add(cls)
        mcs._maybe_register_sub_cmd(cls, bases, choice, choices, help)
        if metadata:  # If no overrides were provided, then initialize lazily later
            cls.__metadata = ProgramMetadata.for_command(cls, parent=mcs._from_parent(mcs.meta, bases), **metadata)

        return cls

    @classmethod
    def _maybe_register_sub_cmd(
        mcs, cls, bases: Bases, choice: str = None, choices: Collection[str] = None, help: str = None  # noqa
    ):
        if ABC in bases:
            return
        has_both = choices or choice is not None
        if choices and choice:
            choices = sorted({choice, *choices})
        elif not choices:
            choices = (choice,)

        parent = mcs.parent(cls, False)
        if parent:
            sub_cmd = mcs.params(parent).sub_command
            if sub_cmd is not None:
                for choice in choices:
                    sub_cmd.register_command(choice, cls, help)
            elif has_both:
                warn(
                    f'choices={choices} were not registered for {cls} because'
                    f' its parent={parent!r} has no SubCommand parameter'
                )
        elif has_both:
            warn(f'choices={choices} were not registered for {cls} because it has no parent Command')

    @classmethod
    def _from_parent(mcs, meth: Callable[[CommandCls], T], bases: Bases) -> Optional[T]:
        for base in bases:
            if isinstance(base, mcs):
                return meth(base)
        return None

    # region Config Methods

    @classmethod
    def _prepare_config(mcs, bases: Bases, config: AnyConfig, kwargs: Dict[str, Any]) -> Config:
        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine config={config!r} with keyword config arguments={kwargs}')
            elif isinstance(config, CommandConfig):
                return config
            kwargs = config  # It was a dict

        parent = mcs._from_parent(mcs.config, bases)
        if kwargs or (not parent and ABC not in bases):
            cfg_kwargs = {k: kwargs.pop(k) for k in CommandConfig.FIELDS.intersection(kwargs)}
            return CommandConfig(parents=(parent,) if parent else (), **cfg_kwargs)

        return None

    @classmethod
    def config(mcs, cls: CommandCls) -> Config:
        try:
            return cls.__config  # noqa
        except AttributeError:
            pass
        parent = mcs.parent(cls)
        if parent is not None:
            return mcs.config(parent)
        return None

    # endregion

    @classmethod
    def parent(mcs, cls: CommandCls, include_abc: bool = True) -> Optional[CommandCls]:
        for parent_cls in type.mro(cls)[1:]:
            if isinstance(parent_cls, mcs) and (include_abc or ABC not in parent_cls.__bases__):
                return parent_cls
        return None

    @classmethod
    def params(mcs, cls: CommandCls) -> CommandParameters:
        # Late initialization is necessary to allow late assignment of Parameters for now
        params = cls.__params
        if not params:
            cls.__params = params = CommandParameters(cls, mcs.parent(cls, True), mcs.config(cls))
        return params

    @classmethod
    def meta(mcs, cls: CommandCls) -> Optional[ProgramMetadata]:
        meta = cls.__metadata
        if not meta:
            parent_meta = mcs._from_parent(mcs.meta, type.mro(cls)[1:])
            cls.__metadata = meta = ProgramMetadata.for_command(cls, parent=parent_meta)
        return meta


def get_parent(command: CommandAny, include_abc: bool = True) -> Optional[CommandCls]:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.parent(command, include_abc)


def get_config(command: CommandAny) -> CommandConfig:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.config(command)


def get_params(command: CommandAny) -> CommandParameters:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.params(command)


def get_top_level_commands() -> List[CommandCls]:
    """
    Returns a list of Command subclasses that are inferred to be direct subclasses of :class:`~commands.Command`.

    This was implemented because ``Command.__subclasses__()`` does not release dead references to subclasses quickly
    enough for tests.
    """
    return [cmd for cmd in CommandMeta._commands if sum(isinstance(cls, CommandMeta) for cls in type.mro(cmd)) == 2]
