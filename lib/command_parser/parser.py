"""
:author: Doug Skrypa
"""

import logging
import sys
from collections import deque
from typing import TYPE_CHECKING, Optional, Sequence, Iterator

from .exceptions import CommandDefinitionError, ParameterDefinitionError, UsageError, NoSuchOption, MissingArgument
from .groups import ParameterGroup
from .parameters import SubCommand, BasePositional, BaseOption, Parameter, PassThru
from .utils import Bool

if TYPE_CHECKING:
    from .commands import CommandType

__all__ = ['CommandParser']
log = logging.getLogger(__name__)


class CommandParser:
    parent: Optional['CommandParser'] = None
    sub_command: Optional[SubCommand] = None
    pass_thru: Optional[PassThru] = None
    long_options: dict[str, BaseOption]
    short_options: dict[str, BaseOption]
    short_combinable: dict[str, BaseOption]
    groups: list[ParameterGroup]

    def __init__(self, command: 'CommandType'):
        self.command = command
        self.groups = []
        self._options = []
        self.positionals = []
        # Positionals are not copied from parent because they must be consumed before the child can be picked
        if (parent := getattr(command, '_Command__parent', None)) is not None:  # type: CommandType
            self.parent = parent_parser = parent.parser()
            self.long_options = parent_parser.long_options.copy()
            self.short_options = parent_parser.short_options.copy()
        else:
            parent_parser = None
            self.long_options = {}
            self.short_options = {}

        self.sub_command, short_combinable = self._process_parameters(command, parent_parser)
        # Sort flags by reverse key length, but forward alphabetical key for keys with the same length
        self.short_combinable = {k: v for k, v in sorted(short_combinable.items(), key=lambda kv: (-len(kv[0]), kv[0]))}
        self.parsed = False

    def _process_parameters(self, command: 'CommandType', parent: Optional['CommandParser']):
        short_combinable = parent.short_combinable.copy() if parent is not None else {}
        sub_cmd_param = None
        var_nargs_pos_param = None
        for attr, param in command.__dict__.items():
            if attr.startswith(('__', '_Command__')):
                continue
            elif isinstance(param, BasePositional):
                if var_nargs_pos_param is not None:
                    raise CommandDefinitionError(
                        f'Additional Positional parameters cannot follow {var_nargs_pos_param} because it accepts'
                        f'a variable number of arguments - {param=} is invalid'
                    )
                elif sub_cmd_param is not None:
                    raise CommandDefinitionError(f'Positional {param=} may not follow a previous one: {sub_cmd_param}')

                self.positionals.append(param)
                if isinstance(param, SubCommand) and param.command is command:
                    sub_cmd_param = param
                if param.nargs.variable:
                    var_nargs_pos_param = param
            elif isinstance(param, BaseOption):
                self._options.append(param)
                _update_options(self.long_options, 'long_opts', param, command)
                _update_options(self.short_options, 'short_opts', param, command)
                _update_options(short_combinable, 'short_combinable', param, command)
            elif isinstance(param, ParameterGroup):
                self.groups.append(param)
            elif isinstance(param, PassThru):
                if self.has_pass_thru():
                    raise CommandDefinitionError(f'Invalid PassThru {param=} - it cannot follow another PassThru param')
                self.pass_thru = param

        if sub_cmd_param is not None and not sub_cmd_param.cmd_command_map:
            raise CommandDefinitionError(f'{command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        return sub_cmd_param, short_combinable

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self._options)
        return f'<{self.__class__.__name__}[command={self.command.__name__}, {positionals=}, {options=}]>'

    def __contains__(self, item: str) -> bool:
        """
        :param item: An option string
        :return: True if this parser contains a matching Option parameter, False otherwise
        """
        if (dash_count := item.count('-', 0, 3)) == 2:
            return item.split('=', 1)[0] in self.long_options
        elif dash_count == 1:
            if '=' in item:
                return item.split('=', 1)[0] in self.short_options
            elif item in self.short_options:
                return True
            key, value = item[1], item[2:]
            short_combinable = self.short_combinable
            if (param := short_combinable.get(key)) is None:
                return False
            elif not value or param.would_accept(value):
                return True
            else:
                return all(c in short_combinable for c in item[1:])
        else:
            return False

    def contains(self, item: str) -> bool:
        if item in self:
            return True
        elif (sub_command := self.sub_command) is not None:
            for command in sub_command.cmd_command_map.values():
                if command.parser().contains(item):
                    return True
        return False

    def has_pass_thru(self) -> bool:
        if self.pass_thru:
            return True
        elif parent := self.parent:
            return parent.has_pass_thru()
        return False

    def all_parameters(self) -> Iterator[Parameter]:
        yield from self.positionals
        yield from self._options

    def reset(self):
        # log.debug(f'Resetting parsed values for {self}')
        for param in self.all_parameters():
            param.reset()
        self.parsed = False

    def parse_args(
        self, args: Sequence[str] = None, allow_unknown: Bool = False
    ) -> tuple[Optional['CommandType'], list[str]]:
        self.parsed = True
        # log.debug(f'{self!r}.parse_args({args=}, {allow_unknown=})')
        # parser = _Parser(self)
        # sub_command = self.sub_command
        remaining = _Parser(self).parse_args(sys.argv[1:] if args is None else args)
        # try:
        #     parser.parse_args(sys.argv[1:] if args is None else args)
        # except PositionalsExhausted:
        #     if sub_command is None:
        #         raise
        for group in self.groups:
            group.check_conflicts()

        # remaining = parser.remaining()
        # if sub_command is not None:
        if (sub_command := self.sub_command) is not None:
            return sub_command.result(), remaining
        elif remaining and not allow_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(remaining)))
        else:
            return None, remaining


class _Parser:
    """Stateful parser used for a single pass of argument parsing"""

    def __init__(self, cmd_parser: CommandParser):
        self.cmd_parser = cmd_parser
        self.long_options = cmd_parser.long_options
        self.short_options = cmd_parser.short_options
        self.short_combinable = cmd_parser.short_combinable
        self.deferred = []

    def parse_args(self, args: Sequence[str]):
        args = self.handle_pass_thru(args)
        pos_iter = iter(self.cmd_parser.positionals)
        while args:
            arg = args.popleft()
            if arg == '--' or arg.startswith('---'):
                raise NoSuchOption(f'invalid argument: {arg}')
            elif arg.startswith('--'):
                self.handle_long(arg, args)
            elif arg.startswith('-') and arg != '-':
                self.handle_short(arg, args)
            else:
                try:
                    param = next(pos_iter)  # type: BasePositional
                except StopIteration:
                    self.deferred.append(arg)
                else:
                    found = param.take_action(arg)
                    self.consume_values(param, args, found=found)

        return self.deferred

    def handle_pass_thru(self, args: Sequence[str]) -> deque[str]:
        if (pass_thru := self.cmd_parser.pass_thru) is not None:
            try:
                split_index = args.index('--')
            except ValueError as e:
                if pass_thru.required:
                    raise MissingArgument(pass_thru, "missing pass thru args separated from others with '--'") from e
            else:
                pass_thru.take_action(args[split_index + 1:])
                return deque(args[:split_index])
        return deque(args)

    def handle_long(self, arg: str, args: deque[str]):
        try:
            param, value = self.split_long(arg)
        except KeyError:
            self.deferred.append(arg)
        else:
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(value)
            elif not self.consume_values(param, args) and param.accepts_none:
                param.take_action(None)

    def handle_short(self, arg: str, args: deque[str]):
        if not (param_val_combos := self.split_short(arg)):
            return
        elif len(param_val_combos) == 1:
            param, value = param_val_combos[0]
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(value)
            elif not self.consume_values(param, args) and param.accepts_none:
                param.take_action(None)
        else:
            last = param_val_combos[-1][0]
            for param, _ in param_val_combos[:-1]:
                param.take_action(None)

            if last.accepts_none and not last.accepts_values:
                last.take_action(None)
            elif not self.consume_values(last, args) and last.accepts_none:
                last.take_action(None)

    def split_long(self, arg: str) -> tuple[BaseOption, Optional[str]]:
        try:
            return self.long_options[arg], None
        except KeyError:
            if '=' in arg:
                key, value = arg.split('=', 1)
                return self.long_options[key], value
            else:
                raise

    def split_short(self, arg: str) -> list[tuple[BaseOption, Optional[str]]]:
        try:
            key, value = arg.split('=', 1)
        except ValueError:
            pass
        else:
            if (param := self.short_options.get(key)) is not None:
                return [(param, value)]
            else:
                self.deferred.append(arg)
                return []

        key, value = arg[1], arg[2:]
        short_combinable = self.short_combinable
        if (param := short_combinable.get(key)) is None:
            self.deferred.append(arg)
            return []
        elif not value:
            return [(param, None)]
        elif param.would_accept(value):
            return [(param, value)]
        else:
            try:
                return [(short_combinable[c], None) for c in arg[1:]]
            except KeyError:
                self.deferred.append(arg)
                return []

    def consume_values(self, param: Parameter, args: deque[str], found: int = 0) -> int:
        result = self._consume_values(param, args, found)
        param.result()  # Trigger validation errors, if any
        return result

    def _consume_values(self, param: Parameter, args: deque[str], found: int = 0) -> int:
        nargs = param.nargs
        while True:
            try:
                value = args.popleft()
            except IndexError as e:
                if nargs.satisfied(found):
                    return found
                raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}') from e
            else:
                if value.startswith('--'):
                    if nargs.satisfied(found):
                        args.appendleft(value)
                        return found
                    raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                elif value.startswith('-') and value != '-':
                    if self.cmd_parser.contains(value):
                        if nargs.satisfied(found):
                            args.appendleft(value)
                            return found
                        raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                    elif not param.would_accept(value):
                        if nargs.satisfied(found):
                            args.appendleft(value)
                            return found
                        raise NoSuchOption(f'invalid argument: {value}')

                try:
                    found += param.take_action(value)
                except UsageError:
                    if nargs.satisfied(found):
                        args.appendleft(value)
                        return found
                    else:
                        raise


def _update_options(opt_dict: dict[str, BaseOption], attr: str, param: BaseOption, command: 'CommandType'):
    for opt in getattr(param, attr):
        try:
            existing = opt_dict[opt]
        except KeyError:
            opt_dict[opt] = param
        else:
            opt_type_names = {
                'long_opts': 'long option', 'short_opts': 'short option', 'short_combinable': 'combinable short option'
            }
            opt_type = opt_type_names[attr]
            raise ParameterDefinitionError(
                f'{opt_type}={opt!r} conflict for {command=} between params {existing} and {param}'
            )
