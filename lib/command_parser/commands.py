"""
:author: Doug Skrypa
"""

import logging
import sys
from typing import Type, TypeVar, Sequence, Optional

from .parameters import Option, Flag, Counter, SubCommand, Action
from .exceptions import CommandDefinitionError
from .groups import ParameterGroup
from .parser import CommandParser
from .utils import Bool

__all__ = ['Command', 'CommandType']
log = logging.getLogger(__name__)

CommandType = TypeVar('CommandType', bound=Type['Command'])


class Command:
    # fmt: off
    __prog: str = None                          # The name of the program (default: sys.argv[0])
    __usage: str = None                         # Usage message (default: auto-generated)
    __description: str = None                   # Description of what the program does
    __epilog: str = None                        # Text to follow parameter descriptions
    __parser: Optional[CommandParser] = None    # The CommandParser used by this Command
    # Attributes related to sub-commands/actions
    __cmd: str = None                           # SubCommand value that maps to this command
    __help: str = None                          # Help text to be displayed as a SubCommand option
    __parent: Type['Command'] = None            # Parent command for sub-commands
    __sub_command: SubCommand = None            # A SubCommand parameter, if provided
    __action: Action = None                     # An Action parameter, if provided
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
        parent = next((c for c in cls.mro() if issubclass(c, Command) and c != cls and c is not Command), None)
        if cmd and parent:
            cls.__parent = parent
            try:
                sub_cmd = parent.__sub_command
            except AttributeError as e:
                raise CommandDefinitionError(
                    f'{cls} cannot extend {parent=} with {cmd=} - no SubCommand parameter was found in {parent}'
                ) from e
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

    def __new__(cls, args: Sequence[str] = None):
        parser = cls.parser()
        if parser.parsed:
            parser.reset()

        sub_cmd, remaining = parser.parse_args(args)
        if sub_cmd is not None and sub_cmd is not cls:
            # log.debug(f'Passing {remaining=} to be parsed by {sub_cmd}')
            return sub_cmd.__new__(sub_cmd, remaining)
        else:
            return super().__new__(cls)

    def __init__(self, args: Sequence[str] = None):
        pass

    def main(self, *args, **kwargs):
        if (action_method := self.__action) is not None:
            action_method(self, *args, **kwargs)

    def __run_main(self, *args, **kwargs):
        try:
            self.main(*args, **kwargs)
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

    def run(self, *args, close_stdout: Bool = False, **kwargs):
        try:
            self.__run_main(*args, **kwargs)
        except KeyboardInterrupt:
            print()
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
