"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

import logging
import sys
from typing import Type, TypeVar, Sequence, Optional
from warnings import warn

from .parameters import ActionFlag, action_flag
from .error_handling import ErrorHandler, extended_error_handler, error_handler as _error_handler
from .exceptions import ParserExit
from .parser import CommandParser
from .utils import _NotSet, Args, Bool, ProgramMetadata

__all__ = ['BaseCommand', 'Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['BaseCommand'])


class BaseCommand:
    """
    Base class for Commands that provides all of the core functionality.  It is generally recommended to extend
    :class:`Command` instead unless you need to omit/re-define the ``--help`` action or any other behavior that strays
    from the core functionality.
    """

    # region Initialization
    # TODO: Single public `command_settings` attr to hold settings
    # fmt: off
    __args: Args                                        # The raw and parsed arguments passed to this command
    args: Args                                          # Same as __args, but can be overwritten.  Not used internally.
    __meta: ProgramMetadata = None                      # Metadata used in help text
    __parser: Optional[CommandParser] = None            # The CommandParser used by this command
    __error_handler: Optional[ErrorHandler] = _NotSet   # The ExceptionHandler to wrap main()
    # Attributes related to sub-commands/actions
    __abstract: Bool = True                             # False if viable for containing sub commands
    __allow_multiple_action_flags: Bool = False         # True to allow multiple action flags to be specified and run
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
        allow_multiple_action_flags: Bool = False,
    ):  # noqa
        """
        :param choice: SubCommand value that maps to this command
        :param prog: The name of the program (default: sys.argv[0])
        :param usage: Usage message (default: auto-generated)
        :param description: Description of what the program does
        :param epilog: Text to follow parameter descriptions
        :param help: Help text to be displayed as a SubCommand option.  Ignored for top-level commands.
        :param error_handler: The ExceptionHandler to be used by :meth:`.run` to wrap :meth:`.main`
        :param abstract: Set to True to prevent a command from being considered to be a parent that may contain sub
          commands
        """
        if cls.__meta is None or prog or usage or description or epilog:  # Inherit from parent when possible
            cls.__meta = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)

        cls.__parser = None
        cls.__abstract = abstract
        cls.__allow_multiple_action_flags = allow_multiple_action_flags
        if error_handler is not _NotSet:
            cls.__error_handler = error_handler

        if parent := next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and not c.__abstract), None):
            if (sub_cmd := parent.parser().sub_command) is not None:
                sub_cmd.register_command(choice, cls, help)
            elif choice:
                warn(f'{choice=} was not registered for {cls} because its {parent=} has no SubCommand parameter')
        elif choice:
            warn(f'{choice=} was not registered for {cls} because it has no parent Command')

    @classmethod
    def parser(cls) -> CommandParser:
        if cls.__parser is None:
            # The parent here is different than in __init_subclass__ to allow ActionFlag inheritance
            parent = next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and c is not BaseCommand), None)
            cls.__parser = CommandParser(cls, parent)
        return cls.__parser

    def __new__(cls, args: Args):
        # By storing the parsed Args here instead of __init__, every single sub class won't need to
        # call super().__init__(...) from their own __init__ for this step
        self = super().__new__(cls)
        self.__args = args
        self.__dict__.setdefault('args', args)
        return self

    # endregion

    @classmethod
    def parse_and_run(cls, argv: Sequence[str] = None, *args, allow_unknown: Bool = False, **kwargs):
        """
        Primary entry point for parsing arguments, resolving sub-commands, and running a command.  Calls :meth:`.parse`
        to parse arguments and resolve sub-commands, then calls :meth:`.run` on the resulting Command instance.  Handles
        exceptions during parsing using the configured :class:`ErrorHandler`.

        To be able to store a reference to the (possibly resolved sub-command) command instance, you should instead use
        the above mentioned methods separately.

        :param argv: The arguments to parse (defaults to ``sys.argv``)
        :param args: Positional arguments to pass to :meth:`.run`
        :param allow_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :param kwargs: Keyword arguments to pass to :meth:`.run`
        """
        error_handler = _error_handler if cls.__error_handler is _NotSet else cls.__error_handler
        if error_handler is not None:
            with error_handler:
                self = cls.parse(argv, allow_unknown)
        else:
            self = cls.parse(argv, allow_unknown)

        try:
            run = self.run
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            pass
        else:
            run(*args, **kwargs)

    @classmethod
    def parse(cls, args: Sequence[str] = None, allow_unknown: Bool = False) -> 'BaseCommand':
        """
        Parses the specified arguments (or ``sys.argv``), and resolves the final sub-command class based on the parsed
        arguments, if necessary.

        :param args: The arguments to parse (defaults to ``sys.argv``)
        :param allow_unknown: Whether unknown arguments should be allowed (default: raise an exception when unknown
          arguments are encountered)
        :return: A Command instance with parsed arguments that is ready for :meth:`.run` or :meth:`.main`
        """
        args = Args(args)
        cmd_cls = cls
        while sub_cmd := cmd_cls.parser().parse_args(args, allow_unknown):
            cmd_cls = sub_cmd

        return cmd_cls(args)

    def run(self, *args, **kwargs):
        """
        Primary entry point for running a command.  Calls :meth:`.main` and handles exceptions using the configured
        :class:`ErrorHandler`.  Alternate error handlers can be specified during Command class initialization.  To skip
        error handling, call :meth:`.main` directly or define the class with ``error_handler=None``.

        :param args: Positional arguments to pass to :meth:`.main`
        :param kwargs: Keyword arguments to pass to :meth:`.main`
        """
        error_handler = _error_handler if self.__error_handler is _NotSet else self.__error_handler
        if error_handler is not None:
            with error_handler:
                self.main(*args, **kwargs)
        else:
            self.main(*args, **kwargs)

    def main(self, *args, **kwargs) -> int:
        """
        If any arguments were specified that are associated with triggering an action method, then that method is called
        here.  Subclasses can override this method if they have only one action, if they need to override the action
        handling logic here, or if they have code that should run based on whether an action was executed or not.

        Initialization code that is common for all actions should be placed in ``__init__`` instead of overriding main.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: The number of actions that were taken
        """
        if action_flags := self.__args.find_all(ActionFlag):
            i = 0
            for i, param in enumerate(sorted(action_flags, key=lambda p: p.order), 1):
                param.func(self, *args, **kwargs)  # noqa
                if not self.__allow_multiple_action_flags:
                    break
            return i
        elif (action := self.parser().action) is not None:
            action.__get__(self, self.__class__)(self, *args, **kwargs)
            return 1
        return 0


class Command(BaseCommand, error_handler=extended_error_handler, abstract=True):
    """
    The main class that other Commands should extend.  Provides the ``--help`` action and handles more Exceptions by
    default, compared to :class:`BaseCommand`.
    """

    @action_flag('-h', order=float('-inf'), help='Show this help message and exit')
    def help(self):
        parser: CommandParser = self.parser()
        print(parser.formatter.format_help())
        raise ParserExit

    def run(self, *args, close_stdout: Bool = False, **kwargs):  # noqa
        try:
            super().run(*args, **kwargs)
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
