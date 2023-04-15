"""
Core classes / functions for Commands, including the metaclass used for Commands, and utilities for finding the primary
top-level Command.

:author: Doug Skrypa
"""

from __future__ import annotations

from abc import ABC, ABCMeta
from typing import TYPE_CHECKING, Optional, Union, TypeVar, Callable, Iterable, Collection, Any, Mapping, Sequence
from typing import Dict, Tuple, List
from warnings import warn
from weakref import WeakSet

from .command_parameters import CommandParameters
from .config import CommandConfig
from .exceptions import CommandDefinitionError
from .metadata import ProgramMetadata

if TYPE_CHECKING:
    from .typing import Config, AnyConfig, CommandCls, CommandAny, OptStr, Bool

__all__ = ['CommandMeta', 'get_parent', 'get_config', 'get_params', 'get_metadata', 'get_top_level_commands']

Bases = Union[Tuple[type, ...], Iterable[type]]
Choices = Union[Mapping[str, Optional[str]], Collection[str]]
T = TypeVar('T')


class CommandMeta(ABCMeta, type):
    # noinspection PyUnresolvedReferences
    """
    :param choice: SubCommand value to map to this command.
    :param choices: SubCommand values to map to this command.  Optionally, a mapping of ``{choice: help text}`` may be
      provided to customize the help text displayed for each choice.
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
        choices: Choices = None,
        help: str = None,  # noqa
        config: AnyConfig = None,
        **kwargs,
    ) -> CommandCls:
        meta_iter = ((k, kwargs.pop(k, None)) for k in ('prog', 'usage', 'description', 'epilog', 'doc_name'))
        metadata = {k: v for k, v in meta_iter if v}
        namespace['_CommandMeta__params'] = None  # Prevent commands from inheriting parent params
        namespace['_CommandMeta__metadata'] = None  # Prevent commands from inheriting parent metadata directly
        namespace['_CommandMeta__parents'] = None  # Prevent commands from inheriting parents directly

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
        mcs, cls, bases: Bases, choice: str = None, choices: Choices = None, help: str = None  # noqa
    ):
        if ABC in bases:
            return
        has_both = choices or choice is not None
        parent = mcs.parent(cls, False)
        if parent:
            sub_cmd = mcs.params(parent).sub_command
            if sub_cmd:
                for choice, choice_help in _choice_items(choice, choices):
                    sub_cmd.register_command(choice, cls, choice_help or help)
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
    def config(mcs, cls: CommandAny) -> Config:
        try:
            return cls.__config     # This attr is not overwritten for every subclass
        except AttributeError:      # This means that the Command and all of its parents have no custom config
            return None

    # endregion

    @classmethod
    def parent(mcs, cls: CommandAny, include_abc: bool = True) -> Optional[CommandCls]:
        """
        :param cls: A Command class or object
        :param include_abc: If True, the first Command parent class in the given Command's mro will be returned,
          regardless of whether that class extends ABC or not.  If False, then the first Command parent class that does
          NOT extend ABC will be returned.
        :return: The given Command's parent Command, or None if no parent was found (which may depend on
          ``include_abc``).
        """
        try:
            first, parent = cls.__parents  # Works for both Command objects and classes
        except TypeError:
            pass
        else:
            return first if include_abc else parent

        cls, mro = _mro(cls)
        first = parent = None
        for parent_cls in mro:
            if isinstance(parent_cls, mcs):
                if first is None:
                    first = parent_cls
                if ABC not in parent_cls.__bases__:
                    parent = parent_cls
                    break

        cls.__parents = first, parent
        return first if include_abc else parent

    @classmethod
    def params(mcs, cls: CommandCls) -> CommandParameters:
        # Late initialization is necessary to allow late assignment of Parameters for now
        try:
            params = cls.__params
        except AttributeError:
            raise TypeError('CommandParameters are only available for Command subclasses') from None
        if not params:
            cls.__params = params = CommandParameters(cls, mcs.parent(cls, True), mcs.config(cls))
        return params

    @classmethod
    def meta(mcs, cls: CommandCls, no_sys_argv: Bool = False) -> Optional[ProgramMetadata]:
        meta = cls.__metadata
        if not meta:
            parent_meta = mcs._from_parent(mcs.meta, type.mro(cls)[1:])
            cls.__metadata = meta = ProgramMetadata.for_command(cls, parent=parent_meta, no_sys_argv=no_sys_argv)
        return meta


def _mro(cmd_cls):
    try:
        return cmd_cls, type.mro(cmd_cls)[1:-1]  # 0 is always the class itself, -1 is always object
    except TypeError:  # a Command object was provided instead of a Command class
        cmd_cls = cmd_cls.__class__
        return cmd_cls, type.mro(cmd_cls)[1:-1]


def _choice_items(choice: OptStr, choices: Optional[Choices]) -> Sequence[Tuple[OptStr, OptStr]]:
    if not choices:
        return ((choice, None),)  # noqa

    try:
        items = {kv: None for kv in choices.items()}
    except AttributeError:
        items = {(c, None): None for c in choices}

    if choice:
        return {(choice, None): None, **items}
    else:
        return items


get_parent = CommandMeta.parent
get_config = CommandMeta.config
get_metadata = CommandMeta.meta


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
