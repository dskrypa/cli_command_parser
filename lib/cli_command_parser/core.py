"""
:author: Doug Skrypa
"""

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


class CommandMeta(ABCMeta, type):
    _tmp_configs = {}
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
        doc_name: str = None,
        config: Union[CommandConfig, Dict[str, Any]] = None,
        **kwargs,
    ):
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
        config_key = '{__module__}.{__qualname__}'.format(**namespace)
        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine config={config!r} with keyword config arguments={kwargs}')
            if not isinstance(config, CommandConfig):
                config = CommandConfig(**config)
            mcls._tmp_configs[config_key] = config
        else:
            config = mcls._config_from_bases(bases)
            if kwargs or (config is None and ABC not in bases):
                if config is not None:
                    # kwargs = config.as_dict() | kwargs
                    for key, val in config.as_dict().items():  # py < 3.9 compatibility
                        kwargs.setdefault(key, val)

                mcls._tmp_configs[config_key] = CommandConfig(**kwargs)

        cls = super().__new__(mcls, name, bases, namespace)
        try:
            # The temp config setting above is to work around __set_name__ happening in super().__new__
            mcls._configs[cls] = mcls._tmp_configs.pop(config_key)
        except KeyError:
            pass
        mcls._commands.add(cls)
        meta = mcls.meta(cls)
        doc = cls.__doc__
        if meta is None or prog or usage or description or epilog or doc_name or doc:
            # Inherit from parent when possible
            mcls._metadata[cls] = ProgramMetadata(
                prog=prog, usage=usage, description=description, epilog=epilog, doc_name=doc_name, doc=doc
            )

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

    @classmethod
    def _config_from_bases(mcls, bases: Tuple[type]) -> Optional[CommandConfig]:
        for base in bases:
            if isinstance(base, mcls):
                return mcls.config(base)
        return None

    def config(cls) -> Optional[CommandConfig]:
        mcls = cls.__class__
        try:
            return mcls._configs[cls]
        except KeyError:
            pass
        try:
            return mcls._tmp_configs[f'{cls.__module__}.{cls.__qualname__}']
        except KeyError:
            pass
        parent = mcls.parent(cls)
        if parent is not None:
            return mcls.config(parent)
        return None

    def params(cls) -> CommandParameters:
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


def get_parent(command: Union[CommandMeta, 'Command'], include_abc: bool = True) -> Optional[CommandMeta]:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.parent(command, include_abc)


def get_config(command: Union[CommandMeta, 'Command']) -> CommandConfig:
    if not isinstance(command, CommandMeta):
        command = command.__class__
    return CommandMeta.config(command)


def get_params(command: Union[CommandMeta, 'Command']) -> 'CommandParameters':
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
