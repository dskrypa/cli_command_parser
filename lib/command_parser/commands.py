"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

import logging
import sys
from dataclasses import asdict
from typing import Type, TypeVar, Sequence, Optional, Union
from warnings import warn

from .args import Args
from .config import CommandConfig
from .error_handling import ErrorHandler, NullErrorHandler, extended_error_handler, error_handler as _error_handler
from .exceptions import ParserExit, CommandDefinitionError, ParamConflict
from .parameters import action_flag
from .parser import CommandParser
from .utils import _NotSet, Bool, ProgramMetadata, classproperty

__all__ = ['BaseCommand', 'Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['BaseCommand'])
CommandObj = TypeVar('CommandObj', bound='BaseCommand')


class BaseCommand:
    """
    Base class for Commands that provides all of the core functionality.  It is generally recommended to extend
    :class:`Command` instead unless you need to omit/re-define the ``--help`` action or any other behavior that strays
    from the core functionality.
    """

    # region Initialization
    # fmt: off
    parser: CommandParser                               # Must declare here for PyCharm's type checker to work properly
    command_config: CommandConfig                       # Must declare here for PyCharm's type checker to work properly
    __args: Args                                        # The raw and parsed arguments passed to this command
    args: Args                                          # Same as __args, but can be overwritten.  Not used internally.
    __command_config: CommandConfig = None              # Configured Command options
    __meta: ProgramMetadata = None                      # Metadata used in help text
    __parser: Optional[CommandParser] = None            # The CommandParser used by this command
    __error_handler: Optional[ErrorHandler] = _NotSet   # The ErrorHandler to wrap main()
    __abstract: Bool = True                             # False if viable for containing sub commands
    # fmt: on

    def __init_subclass__(
        cls: CommandType,
        choice: str = None,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        help: str = None,  # noqa
        error_handler: ErrorHandler = _NotSet,
        abstract: Bool = False,
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
        :param abstract: Set to True to prevent a command from being considered to be a parent that may contain sub
          commands
        """
        if cls.__meta is None or prog or usage or description or epilog:  # Inherit from parent when possible
            cls.__meta = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)

        if config is not None:
            if kwargs:
                raise CommandDefinitionError(f'Cannot combine {config=} with keyword config arguments={kwargs}')
            cls.__command_config = config
        elif kwargs or (cls.__command_config is None and not abstract):
            if cls.__command_config is not None:  # Inherit existing configs and override specified values
                kwargs = asdict(cls.__command_config) | kwargs
            cls.__command_config = CommandConfig(**kwargs)

        cls.__parser = None
        cls.__abstract = abstract
        if error_handler is not _NotSet:
            cls.__error_handler = error_handler

        if parent := next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and not c.__abstract), None):
            if (sub_cmd := parent.parser.sub_command) is not None:  # noqa
                sub_cmd.register_command(choice, cls, help)
            elif choice:
                warn(f'{choice=} was not registered for {cls} because its {parent=} has no SubCommand parameter')
        elif choice:
            warn(f'{choice=} was not registered for {cls} because it has no parent Command')

    @classproperty
    def parser(cls: CommandType) -> CommandParser:  # noqa
        if cls.__parser is None:
            # The parent here is different than in __init_subclass__ to allow ActionFlag inheritance
            parent = next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and c is not BaseCommand), None)
            cls.__parser = CommandParser(cls, parent)
        return cls.__parser

    @classproperty
    def command_config(cls) -> CommandConfig:  # noqa
        return cls.__command_config

    @classmethod
    def __get_error_handler(cls) -> Union[ErrorHandler, NullErrorHandler]:
        if (error_handler := cls.__error_handler) is _NotSet:
            return _error_handler
        elif error_handler is None:
            return NullErrorHandler()
        else:
            return error_handler

    def __new__(cls, args: Args):
        # By storing the parsed Args here instead of __init__, every single sub class won't need to
        # call super().__init__(...) from their own __init__ for this step
        self = super().__new__(cls)
        self.__args = args
        self.__dict__.setdefault('args', args)
        return self

    # endregion

    @classmethod
    def parse_and_run(
        cls, argv: Sequence[str] = None, *args, allow_unknown: Bool = False, **kwargs
    ) -> Optional[CommandObj]:
        """
        Primary entry point for parsing arguments, resolving sub-commands, and running a command.  Calls :meth:`.parse`
        to parse arguments and resolve sub-commands, then calls :meth:`.run` on the resulting Command instance.  Handles
        exceptions during parsing using the configured :class:`ErrorHandler
        <command_parser.error_handling.ErrorHandler>`.

        To be able to store a reference to the (possibly resolved sub-command) command instance, you should instead use
        the above mentioned methods separately.

        :param argv: The arguments to parse (defaults to :data:`sys.argv`)
        :param args: Positional arguments to pass to :meth:`.run`
        :param allow_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :param kwargs: Keyword arguments to pass to :meth:`.run`
        :return: The Command instance with parsed arguments for which :meth:`.run` was already called.
        """
        with cls.__get_error_handler():
            self = cls.parse(argv, allow_unknown)

        try:
            run = self.run
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            return None
        else:
            run(*args, **kwargs)
            return self

    @classmethod
    def parse(cls, args: Sequence[str] = None, allow_unknown: Bool = False) -> CommandObj:
        """
        Parses the specified arguments (or :data:`sys.argv`), and resolves the final sub-command class based on the
        parsed arguments, if necessary.

        :param args: The arguments to parse (defaults to :data:`sys.argv`)
        :param allow_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :return: A Command instance with parsed arguments that is ready for :meth:`.run` or :meth:`.main`
        """
        args = Args(args)
        cmd_cls = cls
        while sub_cmd := cmd_cls.parser.parse_args(args, allow_unknown):
            cmd_cls = sub_cmd

        return cmd_cls(args)

    def run(self, *args, **kwargs) -> int:
        """
        Primary entry point for running a command.  Subclasses generally should not override this method.

        Handles exceptions using the configured :class:`~.error_handling.ErrorHandler`.  Alternate error handlers can
        be specified via the :paramref:`~BaseCommand.__init_subclass__.error_handler` parameter during Command class
        initialization.  To skip error handling, define the class with ``error_handler=None``.

        Calls 3 methods in order: :meth:`.before_main`, :meth:`.main`, and :meth:`.after_main`.

        :param args: Positional arguments to pass to :meth:`.before_main`, :meth:`.main`, and :meth:`.after_main`
        :param kwargs: Keyword arguments to pass to :meth:`.before_main`, :meth:`.main`, and :meth:`.after_main`
        :return: The total number of actions that were taken
        """
        with self.__get_error_handler():
            self.before_main(*args, **kwargs)
            self.main(*args, **kwargs)
            self.after_main(*args, **kwargs)

        return self.__args.actions_taken

    def before_main(self, *args, **kwargs):
        """
        Called by :meth:`.run` before :meth:`.main` is called.  Validates the number of ActionFlags that were specified,
        and calls all of the specified :obj:`~.parameters.before_main` / :obj:`~.parameters.action_flag` actions
        that were defined with ``before_main=True`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.parameters.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.parameters.action_flag` methods
        """
        parsed = self.__args
        action_flags = parsed.action_flags
        if action_flags and not self.__command_config.multiple_action_flags and len(action_flags) > 1:
            raise ParamConflict(action_flags, 'combining multiple action flags is disabled')

        for param in parsed.before_main_actions:
            param.func(self, *args, **kwargs)

    def main(self, *args, **kwargs) -> Optional[int]:
        """
        Primary

        If any arguments were specified that are associated with triggering a method that was decorated / registered as
        a positional :class:`~.parameters.Action`'s target method, then that method is called here.

        Commands that do not have any :class:`~.parameters.Action`s can override this method, and do **not** need
        to call ``super().main(*args, **kwargs)``.

        Initialization code that is common for all actions, or that should be run before :meth:`.before_main` should be
        placed in ``__init__``.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: The total number of actions that were taken so far
        """
        parsed = self.__args
        action = self.parser.action
        if action is not None and (parsed.actions_taken == 0 or self.__command_config.action_after_action_flags):
            # TODO: Error on action when config.action_after_action_flags is False?
            parsed.actions_taken += 1
            action.__get__(self, self.__class__)(self, *args, **kwargs)

        return parsed.actions_taken

    def after_main(self, *args, **kwargs):
        """
        Called by :meth:`.run` after :meth:`.main` is called.  Calls all of the specified
        :obj:`~.parameters.after_main` / :obj:`~.parameters.action_flag` actions that were defined with
        ``before_main=False`` in their configured order.

        :param args: Positional arguments to pass to the :obj:`~.parameters.action_flag` methods
        :param kwargs: Keyword arguments to pass to the :obj:`~.parameters.action_flag` methods
        """
        for param in self.__args.after_main_actions:
            param.func(self, *args, **kwargs)


class Command(BaseCommand, error_handler=extended_error_handler, abstract=True):
    """
    The main class that other Commands should extend.  Provides the ``--help`` action and handles more Exceptions by
    default, compared to :class:`BaseCommand`.
    """

    @action_flag('-h', order=float('-inf'), help='Show this help message and exit')
    def help(self):
        print(self.parser.formatter.format_help())
        raise ParserExit

    def run(self, *args, close_stdout: Bool = False, **kwargs) -> int:
        try:
            return super().run(*args, **kwargs)
        finally:
            if close_stdout:  # TODO: Verify whether this is ever needed anymore
                """
                Prevent the following when piping output to utilities such as ``| head``:
                    Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
                    OSError: [Errno 22] Invalid argument
                """
                try:
                    sys.stdout.close()
                except Exception:
                    pass