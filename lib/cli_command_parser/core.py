"""
:author: Doug Skrypa
"""

from abc import ABC, ABCMeta
from typing import Optional, TypeVar, Type, Any, Dict, Tuple, List
from warnings import warn
from weakref import WeakKeyDictionary, WeakSet

from .actions import help_action
from .command_parameters import CommandParameters
from .config import CommandConfig
from .exceptions import CommandDefinitionError
from .utils import ProgramMetadata


class CommandMeta(ABCMeta, type):
    _configs = WeakKeyDictionary()
    _params = WeakKeyDictionary()
    _metadata = WeakKeyDictionary()
    _commands = WeakSet()

    def __new__(  # noqa
        mcls,  # noqa
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        *,
        choice: str = None,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        help: str = None,  # noqa
        config: CommandConfig = None,
        **kwargs,
    ):
        """
        :param choice: SubCommand value that maps to this command
        :param prog: The name of the program (default: ``sys.argv[0]``)
        :param usage: Usage message (default: auto-generated)
        :param description: Description of what the program does
        :param epilog: Text to follow parameter descriptions
        :param help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
        :param error_handler: The :class:`ErrorHandler<command_parser.error_handling.ErrorHandler>` to be used by
          :meth:`.run` to wrap :meth:`.main`
        :param bool add_help: Whether the --help / -h action_flag should be added
        :param bool action_after_action_flags: Whether action_flag methods are allowed to be combined with a positional
          Action method in a given CLI invocation
        :param bool multiple_action_flags: Whether multiple action_flag methods are allowed to run if they are all
          specified
        :param ignore_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :param allow_missing: Whether missing required arguments should be allowed (default: raise an exception when
          required arguments are missing)
        """
        cls = super().__new__(mcls, name, bases, namespace)
        mcls._commands.add(cls)
        if mcls.meta(cls) is None or prog or usage or description or epilog:  # Inherit from parent when possible
            mcls._metadata[cls] = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)

        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine config={config!r} with keyword config arguments={kwargs}')
            mcls._configs[cls] = config
        else:
            config = mcls.config(cls)
            if kwargs or (config is None and ABC not in bases):
                if config is not None:
                    # kwargs = config.as_dict() | kwargs
                    for key, val in config.as_dict().items():  # py < 3.9 compatibility
                        kwargs.setdefault(key, val)

                mcls._configs[cls] = CommandConfig(**kwargs)

        config = mcls.config(cls)
        if config is not None and config.add_help and not hasattr(cls, '_CommandMeta__help'):
            cls.__help = help_action

        parent = mcls.parent(cls, False)
        if parent:
            sub_cmd = mcls.params(parent).sub_command
            if sub_cmd is not None:
                sub_cmd.register_command(choice, cls, help)
            elif choice:
                warn(
                    f'choice={choice!r} was not registered for {cls} because'
                    f' its parent={parent!r} has no SubCommand parameter'
                )
        elif choice:
            warn(f'choice={choice!r} was not registered for {cls} because it has no parent Command')

        return cls

    def parent(cls, include_abc: bool = True) -> Optional['CommandMeta']:
        for parent_cls in type.mro(cls)[1:]:
            if isinstance(parent_cls, CommandMeta) and (include_abc or ABC not in parent_cls.__bases__):
                return parent_cls
        return None

    def config(cls) -> Optional[CommandConfig]:
        mcls = cls.__class__
        try:
            return mcls._configs[cls]
        except KeyError:
            parent = mcls.parent(cls)
            if parent is not None:
                return mcls.config(parent)
            return None

    def params(cls) -> 'CommandParameters':
        mcls = cls.__class__
        try:
            return mcls._params[cls]
        except KeyError:
            parent = mcls.parent(cls, False)
            mcls._params[cls] = params = CommandParameters(cls, parent)
            return params

    def meta(cls) -> Optional[ProgramMetadata]:
        mcls = cls.__class__
        try:
            return mcls._metadata[cls]
        except KeyError:
            parent = mcls.parent(cls)
            if parent is not None:
                return mcls.meta(parent)
            return None


def get_parent(command: CommandMeta, include_abc: bool = True) -> Optional[CommandMeta]:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.parent(command, include_abc)


def get_config(command: CommandMeta) -> CommandConfig:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.config(command)


def get_params(command: CommandMeta) -> 'CommandParameters':
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.params(command)


def get_top_level_commands() -> List[CommandMeta]:
    """
    Returns a list of Command subclasses that are inferred to be direct subclasses of :class:`~commands.Command`.

    This was implemented because ``Command.__subclasses__()`` does not release dead references to subclasses quickly
    enough for tests.
    """
    return [cmd for cmd in CommandMeta._commands if sum(isinstance(cls, CommandMeta) for cls in cmd.mro()) == 2]


CommandType = TypeVar('CommandType', bound=CommandMeta)
