"""
:author: Doug Skrypa
"""

import logging
import sys
from typing import Type, TypeVar, Sequence, Optional, Union

from .parameters import SubCommand, Action, ActionFlag, action_flag
from .error_handling import ErrorHandler, error_handler, extended_error_handler
from .exceptions import CommandDefinitionError, ParserExit
from .parser import CommandParser
from .utils import Args, Bool, ProgramMetadata

__all__ = ['BaseCommand', 'Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['BaseCommand'])


class BaseCommand:
    # region Initialization
    # fmt: off
    __args: Args                                        # The raw and parsed arguments passed to this command
    __meta: ProgramMetadata = None                      # Metadata used in help text
    # __prog: str = None                                  # The name of the program (default: sys.argv[0])
    # __usage: str = None                                 # Usage message (default: auto-generated)
    # __description: str = None                           # Description of what the program does
    # __epilog: str = None                                # Text to follow parameter descriptions
    __parser: Optional[CommandParser] = None            # The CommandParser used by this command
    __exc_handler: ErrorHandler = None                  # The ExceptionHandler to wrap main()
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
        exc_handler: ErrorHandler = None,
    ):  # noqa
        if cls.__meta is None or prog or usage or description or epilog:  # Inherit from parent when possible
            cls.__meta = ProgramMetadata(prog=prog, usage=usage, description=description, epilog=epilog)
        cls.__cmd = cmd
        cls.__help = help
        cls.__parser = None
        cls.__sub_command = None
        cls.__parent = None
        if exc_handler is not None:
            cls.__exc_handler = exc_handler

        if parent := next((c for c in cls.mro()[1:] if issubclass(c, BaseCommand) and c is not BaseCommand), None):
            cls.__parent = parent
            if cmd and parent is not Command:
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

    def __new__(cls, args: Union[Args, Sequence[str]] = None):
        parser = cls.parser()
        if not isinstance(args, Args):
            args = Args(args)
        if sub_cmd := parser.parse_args(args):
            return sub_cmd.__new__(sub_cmd, args)
        else:
            self = super().__new__(cls)
            self.__args = args
            return self

    def __init__(self, args: Union[Args, Sequence[str]] = None):
        # The 'args' param is ignored here because handling is done in __new__
        if not hasattr(self, 'args'):
            self.args = self.__args

    # endregion

    def main(self, *args, **kwargs):
        if action_flags := self.__args.find_all(ActionFlag):
            param = min(action_flags, key=lambda p: p.priority)
            param.func(self, *args, **kwargs)  # noqa
            return True
        elif (action_method := self.__action) is not None:
            action_method(self, *args, **kwargs)  # noqa  # PyCharm is confused by __call__ vs call after __get__
            return True
        return False

    def print_usage(self):
        pass

    @classmethod
    def parse_and_run(cls, args: Sequence[str] = None, *pargs, **kwargs):
        handler = cls.__exc_handler or error_handler
        with handler:
            self = cls(args)
            self.main(*pargs, **kwargs)

    def run(self, *args, **kwargs):
        handler = self.__exc_handler or error_handler
        with handler:
            self.main(*args, **kwargs)


class Command(BaseCommand, exc_handler=extended_error_handler):
    @action_flag('-h', priority=float('-inf'), help='Show this help message and exit')
    def help(self):
        parser: CommandParser = self.parser()  # noqa  # PyCharm is confused about this for some reason...
        # TODO: --help is not being triggered if there are missing positional args
        # TODO: parent Command args are not showing up in help text
        print(parser.format_usage())
        print(parser.format_help())
        raise ParserExit

    def run(self, *args, close_stdout: Bool = False, **kwargs):
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
