"""
Core classes / functions for Commands, including the metaclass used for Commands, and utilities for finding the primary
top-level Command.

:author: Doug Skrypa
"""

from __future__ import annotations

from abc import ABC, ABCMeta
from typing import TYPE_CHECKING, Any, Callable, Collection, Iterable, Iterator, Mapping, Optional, TypeVar, Union
from warnings import warn
from weakref import WeakSet

from .command_parameters import CommandParameters
from .config import DEFAULT_CONFIG, CommandConfig
from .exceptions import CommandDefinitionError
from .metadata import ProgramMetadata

if TYPE_CHECKING:
    from .typing import AnyConfig, CommandAny, CommandCls, Config, OptStr

    Bases = Union[tuple[type, ...], Iterable[type]]
    Choices = Union[Mapping[str, Optional[str]], Collection[str]]
    OptChoices = Optional[Choices]
    T = TypeVar('T')

__all__ = ['CommandMeta', 'get_parent', 'get_config', 'get_params', 'get_metadata', 'get_top_level_commands']

_NotSet = object()
META_KEYS = {'prog', 'usage', 'description', 'epilog', 'doc_name'}


class CommandMeta(ABCMeta, type):
    # noinspection PyUnresolvedReferences
    """
    :param choice: SubCommand value to map to this command.  If specified, this single choice value will override
      the default value that is based on the name of the class.  Use ``None`` (and do not provide a value for
      ``choices``) to prevent the class from being registered as a subcommand choice.
    :param choices: SubCommand values to map to this command.  Optionally, a mapping of ``{choice: help text}`` may be
      provided to customize the help text displayed for each choice.  If specified, these choice values will
      override the default value that is based on the name of the class.  It is possible, but not necessary, for
      values to be provided for both ``choice`` and this parameter.
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

    @classmethod
    def __prepare__(mcs, name: str, bases: Bases, **kwargs) -> dict[str, Any]:
        """Called before ``__new__`` and before evaluating the contents of a class."""
        return {
            '_CommandMeta__params': None,  # Prevent commands from inheriting parent params
            '_CommandMeta__metadata': None,  # Prevent commands from inheriting parent metadata directly
            '_CommandMeta__parents': None,  # Prevent commands from inheriting parents directly
            '_is_subcommand_': False,
        }

    def __new__(
        mcs,
        name: str,
        bases: Bases,
        namespace: dict[str, Any],
        *,
        choice: str = _NotSet,
        choices: Choices = None,
        help: str = None,  # noqa
        config: AnyConfig = None,
        **kwargs,
    ) -> CommandCls:
        metadata = {k: v for k in META_KEYS.intersection(kwargs) if (v := kwargs.pop(k))}
        if config := mcs._prepare_config(bases, config, kwargs):
            namespace['_CommandMeta__config'] = config

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if metadata:
            # If no overrides were provided, then this is skipped, and it will be initialized lazily later
            # This must be set before calling _maybe_register_sub_cmd so overrides are available during registration
            cls.__metadata = ProgramMetadata.for_command(cls, parent=mcs._from_parent(mcs.meta, bases), **metadata)

        if ABC not in bases:
            mcs._commands.add(cls)
            mcs._maybe_register_sub_cmd(cls, choice, choices, help)

        return cls

    @classmethod
    def _maybe_register_sub_cmd(mcs, cls, choice: OptStr, choices: OptChoices, help: OptStr):  # noqa
        """
        If the given class does not directly extend ABC, and it extends a Command subclass with a :class:`.SubCommand`
        parameter, then this method will register the class as a subcommand choice for that parameter.

        If no explicit ``choice`` or ``choices`` values are provided, then the name of the class (converted from camel
        case to snake case) will be used as the subcommand choice.

        :param cls: A Command (sub)class.
        :param choice: SubCommand value to map to this command.  If specified, this single choice value will override
          the default value that is based on the name of the class.  Use ``None`` (and do not provide a value for
          ``choices``) to prevent the class from being registered as a subcommand choice.
        :param choices: SubCommand values to map to this command.  Optionally, a mapping of ``{choice: help text}`` may
          be provided to customize the help text displayed for each choice.  If specified, these choice values will
          override the default value that is based on the name of the class.  It is possible, but not necessary, for
          values to be provided for both ``choice`` and this parameter.
        :param help: The help text that was provided when the class was defined, if any.
        """
        if parent := mcs.parent(cls, False):
            if sub_cmd := mcs.params(parent).sub_command:
                for choice, choice_help in _choice_items(choice, choices):
                    sub_cmd.register_command(choice, cls, choice_help or help)
            elif choices or (choice is not None and choice is not _NotSet):
                _no_choices_registered_warning(choice, choices, cls, f'its {parent=} has no SubCommand parameter')
        elif choices or (choice is not None and choice is not _NotSet):
            _no_choices_registered_warning(choice, choices, cls, 'it has no parent Command')

    @classmethod
    def _from_parent(mcs, meth: Callable[[CommandCls], T], bases: Bases) -> Optional[T]:
        for base in bases:
            if isinstance(base, mcs):
                return meth(base)
        return None

    # region Config Methods

    @classmethod
    def _prepare_config(mcs, bases: Bases, config: AnyConfig, kwargs: dict[str, Any]) -> Config:
        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine {config=} with keyword config arguments={kwargs}')
            elif isinstance(config, CommandConfig):
                return config
            kwargs = config  # It was a dict

        parent_config = mcs._from_parent(mcs.config, bases)
        if kwargs or (not parent_config and ABC not in bases):
            cfg_kwargs = {k: kwargs.pop(k) for k in CommandConfig.FIELDS.intersection(kwargs)}
            return CommandConfig(parent=parent_config, **cfg_kwargs)

        return None

    @classmethod
    def config(mcs, cls: CommandAny, default: T = None) -> Union[CommandConfig, T]:
        try:
            return cls.__config  # This attr is not overwritten for every subclass
        except AttributeError:  # This means that the Command and all of its parents have no custom config
            return default

    # endregion

    # region Metaclass-Managed Command Attributes

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
    def params(mcs, cls: CommandAny) -> CommandParameters:
        # Late initialization is necessary to allow late assignment of Parameters for now
        try:
            params = cls.__params
        except AttributeError:
            raise TypeError('CommandParameters are only available for Command subclasses') from None
        if not params:
            if not isinstance(cls, mcs):
                cls = cls.__class__
            parent = mcs.parent(cls, True)
            parent_params = mcs.params(parent) if parent is not None else None
            cls.__params = params = CommandParameters(cls, parent, parent_params, mcs.config(cls, DEFAULT_CONFIG))
        return params

    @classmethod
    def meta(mcs, cls: CommandCls) -> ProgramMetadata:
        if not (meta := cls.__metadata):
            parent_meta = mcs._from_parent(mcs.meta, type.mro(cls)[1:])
            cls.__metadata = meta = ProgramMetadata.for_command(cls, parent=parent_meta)
        return meta

    # endregion


def _mro(cmd_cls):
    try:
        return cmd_cls, type.mro(cmd_cls)[1:-1]  # 0 is always the class itself, -1 is always object
    except TypeError:  # a Command object was provided instead of a Command class
        cmd_cls = cmd_cls.__class__
        return cmd_cls, type.mro(cmd_cls)[1:-1]


def _choice_items(choice: OptStr, choices: OptChoices) -> Iterator[tuple[OptStr, OptStr]]:
    if not choices:
        # Automatic use of the subcommand class name is handled by SubCommand.register_command when choice is None
        if choice is not None:  # Allow an explicit None to be used to prevent registration
            yield (None if choice is _NotSet else choice), None
    else:
        try:
            items = choices.items()
        except AttributeError:  # Choices is not a dict of choice:help
            items = ((c, None) for c in choices)

        if choice and choice is not _NotSet and choice not in choices:
            yield choice, None
        yield from items


def _no_choices_registered_warning(choice: OptStr, choices: OptChoices, cls, reason: str):
    if choices and choice is not _NotSet:
        prefix = f'{choice=} and {choices=} were'
    else:
        prefix = f'{choices=} were' if choices else f'{choice=} was'
    warn(f'{prefix} not registered for {cls} because {reason}')


get_parent = CommandMeta.parent
get_config = CommandMeta.config
get_metadata = CommandMeta.meta
get_params = CommandMeta.params


def get_top_level_commands() -> list[CommandCls]:
    """
    Returns a list of Command subclasses that are inferred to be direct subclasses of :class:`~commands.Command`.

    This was implemented because ``Command.__subclasses__()`` does not release dead references to subclasses quickly
    enough for tests.
    """
    return [cmd for cmd in CommandMeta._commands if not cmd._is_subcommand_]
