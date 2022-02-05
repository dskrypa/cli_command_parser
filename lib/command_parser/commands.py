"""
:author: Doug Skrypa
"""

import logging
import sys
from typing import Type, TypeVar, Sequence, Optional, Union

from .parameters import SubCommand, Action, ActionFlag, action_flag
from .exceptions import CommandDefinitionError, ParserExit
from .parser import CommandParser
from .utils import Args, Bool

__all__ = ['BaseCommand', 'Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['BaseCommand'])


class BaseCommand:
    # region Initialization
    # fmt: off
    __args: Args                                # The raw and parsed arguments passed to this command
    __prog: str = None                          # The name of the program (default: sys.argv[0])
    __usage: str = None                         # Usage message (default: auto-generated)
    __description: str = None                   # Description of what the program does
    __epilog: str = None                        # Text to follow parameter descriptions
    __parser: Optional[CommandParser] = None    # The CommandParser used by this command
    # Attributes related to sub-commands/actions
    __cmd: str = None                           # SubCommand value that maps to this command
    __help: str = None                          # Help text to be displayed as a SubCommand option
    __parent: Optional[CommandType] = None      # Parent command for sub-commands
    __sub_command: Optional[SubCommand] = None  # A SubCommand parameter, if provided
    __action: Optional[Action] = None           # An Action parameter, if provided
    # fmt: on

    def __init_subclass__(
        cls: CommandType,
        cmd: str = None,
        prog: str = None,
        usage: str = None,
        description: str = None,
        epilog: str = None,
        help: str = None,  # noqa
    ):  # noqa
        cls.__prog = prog
        cls.__usage = usage
        cls.__description = description
        cls.__epilog = epilog
        cls.__cmd = cmd
        cls.__help = help
        cls.__parser = None
        cls.__sub_command = None
        cls.__parent = None
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

    def run(self, *args, **kwargs):
        try:
            self.main(*args, **kwargs)
        except ParserExit as e:
            e.exit()
        except KeyboardInterrupt:
            print()


class Command(BaseCommand):
    @action_flag('-h', priority=float('-inf'), help='Show this help message and exit')
    def help(self):
        print('TODO: Implement help text')
        # raise ParserExit

    def run(self, *args, close_stdout: Bool = False, **kwargs):
        try:
            self.__run(*args, **kwargs)
        except BrokenPipeError:
            pass
        finally:
            if close_stdout:
                """
                Prevent the following when piping output to utilities such as ``| head``:
                    Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
                    OSError: [Errno 22] Invalid argument
                """
                try:
                    sys.stdout.close()
                except Exception:
                    pass

    def __run(self, *args, **kwargs):
        try:
            super().run(*args, **kwargs)
        except OSError as e:
            import platform

            if platform.system().lower() == 'windows' and e.errno == 22:
                # When using |head, the pipe will be closed when head is done, but Python will still think that it
                # is open - checking whether sys.stdout is writable or closed doesn't work, so triggering the
                # error again seems to be the most reliable way to detect this (hopefully) without false positives
                try:
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                except OSError:
                    pass
                else:
                    raise  # If it wasn't the expected error, let the main Exception handler handle it
            else:
                raise
