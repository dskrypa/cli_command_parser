"""
:author: Doug Skrypa
"""

import logging

# import re
from collections import deque, defaultdict

# from functools import cached_property
from typing import TYPE_CHECKING, Optional, Any, Collection

from .actions import help_action
from .exceptions import (
    CommandDefinitionError,
    ParameterDefinitionError,
    UsageError,
    NoSuchOption,
    MissingArgument,
    ParamsMissing,
)
from .formatting import HelpFormatter
from .parameters import ParameterGroup, Action
from .parameters import SubCommand, BaseOption, Parameter, PassThru, ActionFlag, BasePositional as _Positional
from .utils import Bool

if TYPE_CHECKING:
    from .args import Args
    from .commands import CommandType

__all__ = ['CommandParser']
log = logging.getLogger(__name__)


class CommandParser:
    command: 'CommandType'
    command_parent: Optional['CommandType']
    formatter: HelpFormatter
    parent: Optional['CommandParser'] = None
    sub_command: Optional[SubCommand] = None
    action: Optional[Action] = None
    pass_thru: Optional[PassThru] = None
    groups: list[ParameterGroup]
    options: list[BaseOption]
    positionals: list[_Positional]
    long_options: dict[str, BaseOption]
    short_options: dict[str, BaseOption]
    short_combinable: dict[str, BaseOption]
    action_flags: list[ActionFlag]

    def __init__(self, command: 'CommandType', command_parent: 'CommandType' = None):
        self.command = command
        self.command_parent = command_parent
        self.positionals = []  # Not copied from the parent because they must be consumed before the child can be picked
        self.formatter = HelpFormatter(command, self)
        if command_parent is not None:
            self.parent = parent = command_parent.parser
            self.groups = parent.groups.copy()
            self.options = parent.options.copy()
            self.long_options = parent.long_options.copy()
            self.short_options = parent.short_options.copy()

            self.formatter.maybe_add(*self.options)
        else:
            parent = None
            self.groups = []
            self.options = []
            self.long_options = {}
            self.short_options = {}

        short_combinable = self._process_parameters(self.command, parent)
        # Sort flags by reverse key length, but forward alphabetical key for keys with the same length
        self.short_combinable = {k: v for k, v in sorted(short_combinable.items(), key=lambda kv: (-len(kv[0]), kv[0]))}
        self.action_flags = self._process_action_flags()
        self.groups = sorted(self.groups)

    # @cached_property
    # def has_numeric_short_option(self) -> bool:
    #     if self.parent and self.parent.has_numeric_short_option:
    #         return True
    #     is_numeric = re.compile(r'^-\d+$|^-\d*\.\d+?$').match
    #     return any(map(is_numeric, self.short_options))

    # region Initialization / Parameter Processing

    def _process_parameters(self, command: 'CommandType', parent: Optional['CommandParser']):
        short_combinable = parent.short_combinable.copy() if parent is not None else {}
        var_nargs_pos_param = None
        for attr, param in command.__dict__.items():
            if attr.startswith('__'):
                continue
            elif isinstance(param, _Positional):
                var_nargs_pos_param = self._add_positional(param, var_nargs_pos_param)
            elif isinstance(param, BaseOption):
                self._add_option(param, short_combinable, command)
            elif isinstance(param, ParameterGroup):
                self.formatter.maybe_add(param)
                self.groups.append(param)
            elif isinstance(param, PassThru):
                if self.has_pass_thru():
                    raise CommandDefinitionError(f'Invalid PassThru {param=} - it cannot follow another PassThru param')
                self.formatter.maybe_add(param)
                self.pass_thru = param

        return short_combinable

    def _add_positional(self, param: _Positional, var_nargs_param: Optional[_Positional]) -> Optional[_Positional]:
        if self.sub_command is not None:
            raise CommandDefinitionError(
                f'Positional {param=} may not follow the sub command {self.sub_command} - re-order the positionals,'
                ' move it into the sub command(s), or convert it to an optional parameter'
            )
        elif var_nargs_param is not None:
            raise CommandDefinitionError(
                f'Additional Positional parameters cannot follow {var_nargs_param} because it accepts'
                f' a variable number of arguments with no specific choices defined - {param=} is invalid'
            )

        self.positionals.append(param)
        self.formatter.maybe_add(param)

        if isinstance(param, (SubCommand, Action)) and param.command is self.command:
            if action := self.action:  # self.sub_command being already defined is handled above
                raise CommandDefinitionError(
                    f'Only 1 Action xor SubCommand is allowed in a given Command - {self.command.__name__} cannot'
                    f' contain both {action} and {param}'
                )
            elif isinstance(param, SubCommand):
                self.sub_command = param
            else:
                self.action = param

        if param.nargs.variable and not param.choices:
            return param

        return None

    def _add_option(self, param: BaseOption, short_combinable: dict[str, BaseOption], command: 'CommandType'):
        self.options.append(param)
        self.formatter.maybe_add(param)
        _update_options(self.long_options, 'long_opts', param, command)
        _update_options(self.short_options, 'short_opts', param, command)
        _update_options(short_combinable, 'short_combinable', param, command)

    def _process_action_flags(self):
        action_flags = sorted((p for p in self.options if isinstance(p, ActionFlag)))
        grouped_ordered_flags = {True: defaultdict(list), False: defaultdict(list)}
        for param in action_flags:
            if param.func is None:
                raise ParameterDefinitionError(f'No function was registered for {param=}')
            grouped_ordered_flags[param.before_main][param.order].append(param)

        invalid = {}
        for before_main, prio_params in grouped_ordered_flags.items():
            for prio, params in prio_params.items():  # noqa
                if len(params) > 1:
                    if (group := next((p.group for p in params if p.group), None)) and group.mutually_exclusive:
                        if not all(p.group == group for p in params):
                            invalid[(before_main, prio)] = params
                    else:
                        invalid[(before_main, prio)] = params

        if invalid:
            raise CommandDefinitionError(
                f'ActionFlag parameters with the same before/after main setting must either have different order values'
                f' or be in a mutually exclusive ParameterGroup - invalid parameters: {invalid}'
            )

        return action_flags

    # endregion

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self.options)
        return f'<{self.__class__.__name__}[command={self.command.__name__}, {positionals=}, {options=}]>'

    def contains(self, args: 'Args', item: str, recursive: Bool = True) -> bool:
        if self._contains(args, item):
            return True
        elif recursive and (sub_command := self.sub_command) is not None:
            for choice in sub_command.choices.values():
                if choice.target.parser.contains(args, item, recursive):
                    return True
        return False

    def _contains(self, args: 'Args', item: str) -> bool:
        """
        :param args: The raw / partially parsed arguments for this parser
        :param item: An option string
        :return: True if this parser contains a matching Option parameter, False otherwise
        """
        if item.startswith('---'):
            return False
        elif item.startswith('--'):
            return item.split('=', 1)[0] in self.long_options
        elif item.startswith('-'):
            try:
                item, value = item.split('=', 1)
            except ValueError:
                if item in self.short_options:
                    return True
                # else: process further
            else:
                return item in self.short_options

            key, value = item[1], item[2:]
            short_combinable = self.short_combinable
            if (param := short_combinable.get(key)) is None:
                return False
            elif not value or param.would_accept(args, value):
                return True
            else:
                return all(c in short_combinable for c in item[1:])
        else:
            return False

    def has_pass_thru(self) -> bool:
        if self.pass_thru:
            return True
        elif parent := self.parent:
            return parent.has_pass_thru()
        return False

    def _get_missing(self, args: 'Args') -> list['Parameter']:
        missing_pos: list['Parameter'] = [
            p
            for p in self.positionals
            if p.group is None and args.num_provided(p) == 0 and not isinstance(p, SubCommand)
        ]
        missing_opt = [p for p in self.options if p.required and p.group is None and args.num_provided(p) == 0]
        return missing_pos + missing_opt

    def parse_args(self, args: 'Args', allow_unknown: Bool = False) -> Optional['CommandType']:
        # log.debug(f'{self!r}.parse_args({args=}, {allow_unknown=})')
        if (sub_cmd_param := self.sub_command) is not None and not sub_cmd_param.choices:
            raise CommandDefinitionError(f'{self.command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        _Parser(self, args).parse_args()
        for group in self.groups:
            group.validate(args)

        if (sub_command := self.sub_command) is not None:
            try:
                next_cmd = sub_command.result(args)  # type: CommandType
            except UsageError:
                if help_action not in args:
                    raise
            else:
                if (missing := self._get_missing(args)) and next_cmd.parser.parent is not self.command:
                    if help_action in args:
                        return None
                    raise ParamsMissing(missing)
                return next_cmd
        elif (missing := self._get_missing(args)) and (not self.action or self.action not in missing):
            # The action is excluded because it provides a better error message
            if help_action not in args:
                raise ParamsMissing(missing)
        elif args.remaining and not allow_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(args.remaining)))

        return None

    def arg_dict(self, args: 'Args', exclude: Collection['Parameter'] = ()) -> dict[str, Any]:
        if (parent := self.parent) is not None:
            arg_dict = parent.arg_dict(args)
        else:
            arg_dict = {}

        for group in (self.positionals, self.options):
            for param in group:
                if param not in exclude:
                    arg_dict[param.name] = param.result_value(args)

        return arg_dict


class _Parser:
    """Stateful parser used for a single pass of argument parsing"""

    def __init__(self, cmd_parser: CommandParser, args: 'Args'):
        self.cmd_parser = cmd_parser
        self.long_options = cmd_parser.long_options
        self.short_options = cmd_parser.short_options
        self.short_combinable = cmd_parser.short_combinable
        self.deferred = None
        self.args = args
        positionals = self.cmd_parser.positionals
        self.pos_available = bool(positionals)
        self.pos_iter = iter(positionals)

    def parse_args(self):
        args = self.args
        arg_deque = self.handle_pass_thru()
        self.deferred = args.remaining = []
        while arg_deque:
            arg = arg_deque.popleft()
            if arg == '--' or arg.startswith('---'):
                raise NoSuchOption(f'invalid argument: {arg}')
            elif arg.startswith('--'):
                self.handle_long(arg, arg_deque)
            elif arg.startswith('-') and arg != '-':
                try:
                    self.handle_short(arg, arg_deque)
                except NotAShortOption:
                    if self.pos_available:
                        try:
                            self.handle_positional(arg, arg_deque)
                        except UsageError:
                            self.deferred.append(arg)
                    else:
                        self.deferred.append(arg)
            else:
                self.handle_positional(arg, arg_deque)

    def handle_pass_thru(self) -> deque[str]:
        args = self.args
        remaining = args.remaining
        if (pass_thru := self.cmd_parser.pass_thru) is not None:
            try:
                a = remaining.index('--')
            except ValueError as e:
                if pass_thru.required:
                    raise MissingArgument(pass_thru, "missing pass thru args separated from others with '--'") from e
            else:
                b = a + 1
                pass_thru.take_action(args, remaining[b:])
                return deque(remaining[:a])
        return deque(remaining)

    def handle_positional(self, arg: str, arg_deque: deque[str]):
        try:
            param = next(self.pos_iter)  # type: _Positional
        except StopIteration:
            self.pos_available = False
            self.deferred.append(arg)
        else:
            found = param.take_action(self.args, arg)
            self.consume_values(param, arg_deque, found=found)

    def handle_long(self, arg: str, arg_deque: deque[str]):
        try:
            param, value = self.split_long(arg)
        except KeyError:
            self.deferred.append(arg)
        else:
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(self.args, value)
            elif not self.consume_values(param, arg_deque) and param.accepts_none:
                param.take_action(self.args, None)

    def handle_short(self, arg: str, arg_deque: deque[str]):
        param_val_combos = self.split_short(arg)
        # log.debug(f'Split {arg=} into {param_val_combos=}')
        if len(param_val_combos) == 1:
            param, value = param_val_combos[0]
            self._handle_short_value(param, value, arg_deque)
        else:
            last = param_val_combos[-1][0]
            for param, _ in param_val_combos[:-1]:
                param.take_action(self.args, None)

            self._handle_short_value(last, None, arg_deque)

    def _handle_short_value(self, param: BaseOption, value: Any, arg_deque: deque[str]):
        # log.debug(f'Handling short {value=} for {param=}')
        if value is not None or (param.accepts_none and not param.accepts_values):
            param.take_action(self.args, value)
        elif not self.consume_values(param, arg_deque):
            if param.accepts_none:
                param.take_action(self.args, None)
            else:
                raise MissingArgument(param)

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
            if (param := self.short_options.get(arg)) is not None:
                return [(param, None)]
        else:
            if (param := self.short_options.get(key)) is not None:
                return [(param, value)]
            else:
                raise NotAShortOption

        key, value = arg[1], arg[2:]
        short_combinable = self.short_combinable
        if (param := short_combinable.get(key)) is None:
            raise NotAShortOption
        # elif not value:
        # # Commented out now because this case should be handled by self.short_options.get(arg)
        #     return [(param, None)]
        elif param.would_accept(self.args, value):
            return [(param, value)]
        else:
            try:
                return [(short_combinable[c], None) for c in arg[1:]]
            except KeyError as e:
                raise NotAShortOption from e

    def consume_values(self, param: Parameter, arg_deque: deque[str], found: int = 0) -> int:
        result = self._consume_values(param, arg_deque, found)
        # log.debug(f'_consume_values {result=} for {param=}')
        param.result(self.args)  # Trigger validation errors, if any
        return result

    def _consume_values(self, param: Parameter, arg_deque: deque[str], found: int = 0) -> int:
        nargs = param.nargs
        while True:
            try:
                value = arg_deque.popleft()
            except IndexError as e:
                # log.debug(f'Ran out of values in deque while processing {param=}')
                if nargs.satisfied(found):
                    return found
                raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}') from e
            else:
                # log.debug(f'Found {value=} in deque - may use it for {param=}')
                if value.startswith('--'):
                    if nargs.satisfied(found):
                        arg_deque.appendleft(value)
                        return found
                    raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                elif value.startswith('-') and value != '-':
                    if self.cmd_parser.contains(self.args, value):
                        # log.debug(f'{value=} will not be used with {param=} - it is also a parameter')
                        if nargs.satisfied(found):
                            arg_deque.appendleft(value)
                            return found
                        raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                    elif not param.would_accept(self.args, value):
                        # log.debug(f'{value=} will not be used with {param=} - it would not be accepted')
                        if nargs.satisfied(found):
                            arg_deque.appendleft(value)
                            return found
                        raise NoSuchOption(f'invalid argument: {value}')
                    # log.debug(f'{value=} may be used with {param=} as a value')

                try:
                    found += param.take_action(self.args, value)
                except UsageError:
                    # log.debug(f'{value=} was rejected by {param=}', exc_info=True)
                    if nargs.satisfied(found):
                        arg_deque.appendleft(value)
                        return found
                    else:
                        raise


class NotAShortOption(Exception):
    """Used only during parsing to indicate that a given arg is not a short option"""


def _update_options(opt_dict: dict[str, BaseOption], attr: str, param: BaseOption, command: 'CommandType'):
    for opt in getattr(param, attr):
        try:
            existing = opt_dict[opt]
        except KeyError:
            opt_dict[opt] = param
        else:
            opt_type_names = {
                'long_opts': 'long option',
                'short_opts': 'short option',
                'short_combinable': 'combinable short option',
            }
            opt_type = opt_type_names[attr]
            raise CommandDefinitionError(
                f'{opt_type}={opt!r} conflict for {command=} between params {existing} and {param}'
            )
