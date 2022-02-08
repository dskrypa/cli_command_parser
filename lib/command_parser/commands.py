"""
The core Command classes that are intended as the entry point for a given program.

:author: Doug Skrypa
"""

import logging
import sys
from typing import Type, TypeVar, Sequence, Optional

from .parameters import SubCommand, Action, ActionFlag, action_flag
from .error_handling import ErrorHandler, extended_error_handler, error_handler as _error_handler
from .exceptions import CommandDefinitionError, ParserExit
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
    # fmt: off
    __args: Args                                        # The raw and parsed arguments passed to this command
    args: Args                                          # Same as __args, but can be overwritten.  Not used internally.
    __meta: ProgramMetadata = None                      # Metadata used in help text
    __parser: Optional[CommandParser] = None            # The CommandParser used by this command
    __error_handler: Optional[ErrorHandler] = _NotSet   # The ExceptionHandler to wrap main()
    # Attributes related to sub-commands/actions
    __cmd: str = None                                   # SubCommand value that maps to this command
    __help: str = None                                  # Help text to be displayed as a SubCommand option
    __parent: Optional[CommandType] = None              # Parent command for sub-commands
    __sub_command: Optional[SubCommand] = None          # A SubCommand parameter, if provided
    __action: Optional[Action] = None                   # An Action parameter, if provided
    # fmt: on

    def __init_subclass__(
        cls: CommandType,
        cmd: str = None,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        help: str = None,  # noqa
        error_handler: ErrorHandler = _NotSet,
    ):  # noqa
        """
        :param cmd: SubCommand value that maps to this command
        :param prog: The name of the program (default: sys.argv[0])
        :param usage: Usage message (default: auto-generated)
        :param description: Description of what the program does
        :param epilog: Text to follow parameter descriptions
        :param help: Help text to be displayed as a SubCommand option
        :param error_handler: The ExceptionHandler to be used by :meth:`.run` to wrap :meth:`.main`
        """
        if cls.__meta is None or prog or usage or description or epilog:  # Inherit from parent when possible
            cls.__meta = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)
        cls.__cmd = cmd
        cls.__help = help
        cls.__parser = None
        cls.__sub_command = None
        cls.__parent = None
        if error_handler is not _NotSet:
            cls.__error_handler = error_handler

        if parent := next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and c is not BaseCommand), None):
            cls.__parent = parent
            if cmd and parent not in (Command, BaseCommand):
                if (sub_cmd := parent.__sub_command) is None:
                    raise CommandDefinitionError(
                        f'{cls} cannot extend {parent=} with {cmd=} - no SubCommand parameter was found in {parent}'
                    )
                else:
                    sub_cmd.register(cls)

        last = None
        for key, val in list(cls.__dict__.items()):  # Only examine attrs specific to this subclass
            if not isinstance(val, (SubCommand, Action)):
                continue
            elif last is not None:
                raise CommandDefinitionError(
                    f'Only 1 Action or SubCommand is allowed in a given Command - {cls.__name__} cannot contain both'
                    f' {last} and {val}'
                )
            elif isinstance(val, SubCommand):
                cls.__sub_command = last = val
            elif isinstance(val, Action):
                cls.__action = last = val

    @classmethod
    def parser(cls) -> CommandParser:
        if cls.__parser is None:
            cls.__parser = CommandParser(cls)
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
    def parse_and_run(cls, argv: Sequence[str] = None, *args, **kwargs):
        """
        Primary entry point for parsing arguments, resolving sub-commands, and running a command.  Calls :meth:`.parse`
        to parse arguments and resolve sub-commands, then calls :meth:`.run` on the resulting Command instance.  Handles
        exceptions during parsing using the configured :class:`ErrorHandler`.

        To be able to store a reference to the (possibly resolved sub-command) command instance, you should instead use
        the above mentioned methods separately.

        :param argv: The arguments to parse (defaults to ``sys.argv``)
        :param args: Positional arguments to pass to :meth:`.run`
        :param kwargs: Keyword arguments to pass to :meth:`.run`
        """
        error_handler = _error_handler if cls.__error_handler is _NotSet else cls.__error_handler
        if error_handler is not None:
            with error_handler:
                self = cls.parse(argv)
        else:
            self = cls.parse(argv)

        try:
            run = self.run
        except UnboundLocalError:  # There was an error handled during parsing, so self was not defined
            pass
        else:
            self.run(*args, **kwargs)

    @classmethod
    def parse(cls, args: Sequence[str] = None) -> 'BaseCommand':
        """
        Parses the specified arguments (or ``sys.argv``), and resolves the final sub-command class based on the parsed
        arguments, if necessary.

        :param args: The arguments to parse (defaults to ``sys.argv``)
        :return: A Command instance with parsed arguments that is ready for :meth:`.run` or :meth:`.main`
        """
        args = Args(args)
        cmd_cls = cls
        while sub_cmd := cmd_cls.parser().parse_args(args):  # noqa  # PyCharm is confused about this for some reason...
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

    def main(self, *args, **kwargs) -> bool:
        """
        If any arguments were specified that are associated with triggering an action method, then that method is called
        here.  Subclasses can override this method if they have only one action, if they need to override the action
        handling logic here, or if they have code that should run based on whether an action was executed or not.

        Initialization code that is common for all actions should be placed in ``__init__`` instead of overriding main.

        :param args: Positional arguments to pass to the action method
        :param kwargs: Keyword arguments to pass to the action method
        :return: True if an action method was called, False otherwise
        """
        if action_flags := self.__args.find_all(ActionFlag):
            param = min(action_flags, key=lambda p: p.priority)
            param.func(self, *args, **kwargs)  # noqa
            return True
        elif (action_method := self.__action) is not None:
            action_method(self, *args, **kwargs)  # noqa  # PyCharm is confused by __call__ vs call after __get__
            return True
        return False


class Command(BaseCommand, error_handler=extended_error_handler):
    """
    The main class that other Commands should extend.  Provides the ``--help`` action and handles more Exceptions by
    default, compared to :class:`BaseCommand`.
    """

    @action_flag('-h', priority=float('-inf'), help='Show this help message and exit')
    def help(self):
        parser: CommandParser = self.parser()  # noqa  # PyCharm is confused about this for some reason...
        print(parser.format_help())
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
