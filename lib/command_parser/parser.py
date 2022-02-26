"""
:author: Doug Skrypa
"""

import logging
from collections import deque
from typing import TYPE_CHECKING, Optional, Any

from .actions import help_action
from .exceptions import (
    CommandDefinitionError,
    UsageError,
    NoSuchOption,
    MissingArgument,
    ParamsMissing,
    ParamUsageError,
)
from .parameters import SubCommand, BaseOption, Parameter, BasePositional
from .utils import Bool

if TYPE_CHECKING:
    from .args import Args
    from .commands import CommandType
    from .command_parameters import CommandParameters

__all__ = ['CommandParser']
log = logging.getLogger(__name__)


class CommandParser:
    command: 'CommandType'

    def __init__(self, command: 'CommandType'):
        self.command = command
        self.params: 'CommandParameters' = command.params

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[params={self.params}]>'

    def _get_missing(self, args: 'Args') -> list['Parameter']:
        params = self.params
        missing_pos: list['Parameter'] = [
            p
            for p in params.positionals
            if p.group is None and args.num_provided(p) == 0 and not isinstance(p, SubCommand)
        ]
        missing_opt = [p for p in params.options if p.required and p.group is None and args.num_provided(p) == 0]
        return missing_pos + missing_opt

    def parse_args(
        self,
        args: 'Args',
        allow_unknown: Bool = False,
        allow_missing: Bool = False,
    ) -> Optional['CommandType']:
        # log.debug(f'{self!r}.parse_args({args=}, {allow_unknown=}, {allow_missing=})')
        params = self.params
        if (sub_cmd_param := params.sub_command) is not None and not sub_cmd_param.choices:
            raise CommandDefinitionError(f'{self.command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        _Parser(params, args).parse_args()
        for group in params.groups:
            group.validate(args)

        if sub_cmd_param is not None:
            try:
                next_cmd = sub_cmd_param.result(args)  # type: CommandType
            except UsageError:
                if help_action not in args:
                    raise
            else:
                if (missing := self._get_missing(args)) and next_cmd.params.command_parent is not self.command:
                    if help_action in args:
                        return None
                    raise ParamsMissing(missing)
                return next_cmd
        elif (
            (missing := self._get_missing(args))
            and not allow_missing
            and (
                not params.action or params.action not in missing
            )  # excluded because it provides a better error message
        ):
            if help_action not in args:
                raise ParamsMissing(missing)
        elif args.remaining and not allow_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(args.remaining)))

        return None


class _Parser:
    """Stateful parser used for a single pass of argument parsing"""

    def __init__(self, params: 'CommandParameters', args: 'Args'):
        self.params = params
        self.deferred = None
        self.arg_deque = None
        self.args = args
        self.positionals = params.positionals.copy()

    def parse_args(self):
        self.arg_deque = arg_deque = self.handle_pass_thru()
        self.deferred = self.args.remaining = []
        while arg_deque:
            arg = arg_deque.popleft()
            if arg == '--' or arg.startswith('---'):
                raise NoSuchOption(f'invalid argument: {arg}')
            elif arg.startswith('--'):
                self.handle_long(arg)
            elif arg.startswith('-') and arg != '-':
                try:
                    self.handle_short(arg)
                except KeyError:
                    self._check_sub_command_options(arg)
                    if self.positionals:
                        try:
                            self.handle_positional(arg)
                        except UsageError:
                            self.deferred.append(arg)
                    else:
                        self.deferred.append(arg)
            else:
                self.handle_positional(arg)

    def handle_pass_thru(self) -> deque[str]:
        args = self.args
        remaining = args.remaining
        if (pass_thru := self.params.pass_thru) is not None:
            try:
                separator_pos = remaining.index('--')
            except ValueError as e:
                if pass_thru.required:
                    raise MissingArgument(pass_thru, "missing pass thru args separated from others with '--'") from e
            else:
                remainder_start = separator_pos + 1
                pass_thru.take_action(args, remaining[remainder_start:])
                return deque(remaining[:separator_pos])
        return deque(remaining)

    def handle_positional(self, arg: str):
        # log.debug(f'handle_positional({arg=})')
        try:
            param = self.positionals.pop(0)  # type: BasePositional
        except IndexError:
            self.deferred.append(arg)
        else:
            try:
                found = param.take_action(self.args, arg)
            except UsageError:
                self.positionals.insert(0, param)
                raise
            self.consume_values(param, found=found)

    def handle_long(self, arg: str):
        # log.debug(f'handle_long({arg=})')
        try:
            param, value = self.params.long_option_to_param_value_pair(arg)
        except KeyError:
            self._check_sub_command_options(arg)
            self.deferred.append(arg)
        else:
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(self.args, value)
            elif not self.consume_values(param) and param.accepts_none:
                param.take_action(self.args, None)

    def handle_short(self, arg: str):
        # log.debug(f'handle_short({arg=})')
        param_val_combos = self.params.short_option_to_param_value_pairs(arg)
        # log.debug(f'Split {arg=} into {param_val_combos=}')
        if len(param_val_combos) == 1:
            param, value = param_val_combos[0]
            self._handle_short_value(param, value)
        else:
            last = param_val_combos[-1][0]
            for param, _ in param_val_combos[:-1]:
                param.take_action(self.args, None, short_combo=True)

            self._handle_short_value(last, None)

    def _handle_short_value(self, param: BaseOption, value: Any):
        # log.debug(f'Handling short {value=} for {param=}')
        if value is not None or (param.accepts_none and not param.accepts_values):
            param.take_action(self.args, value, short_combo=True)
        elif not self.consume_values(param) and param.accepts_none:
            param.take_action(self.args, None, short_combo=True)
        # No need to raise MissingArgument if values were not consumed - consume_values handles checking nargs

    def _check_sub_command_options(self, arg: str):
        # log.debug(f'_check_sub_command_options({arg=})')
        # This check is only needed when subcommand option values may be misinterpreted as positional values
        if not self.positionals:
            return
        elif (param := self.params.find_nested_option_that_accepts_values(arg)) is not None:
            raise ParamUsageError(param, 'subcommand arguments must be provided after the subcommand')

    def consume_values(self, param: Parameter, found: int = 0) -> int:
        while True:
            try:
                value = self.arg_deque.popleft()
            except IndexError:
                # log.debug(f'Ran out of values in deque while processing {param=}')
                return self._finalize_consume(param, None, found)
            else:
                # log.debug(f'Found {value=} in deque - may use it for {param=}')
                if value.startswith('--'):
                    return self._finalize_consume(param, value, found)
                elif value.startswith('-') and value != '-':
                    if self.params.get_option_param_value_pairs(value):
                        # log.debug(f'{value=} will not be used with {param=} - it is also a parameter')
                        return self._finalize_consume(param, value, found)
                    else:
                        try:
                            self._check_sub_command_options(value)
                        except ParamUsageError as e:
                            return self._finalize_consume(param, value, found, e)

                    if not param.would_accept(self.args, value):
                        # log.debug(f'{value=} will not be used with {param=} - it would not be accepted')
                        return self._finalize_consume(param, value, found, NoSuchOption(f'invalid argument: {value}'))
                    # log.debug(f'{value=} may be used with {param=} as a value')

                try:
                    found += param.take_action(self.args, value)
                except UsageError as e:
                    # log.debug(f'{value=} was rejected by {param=}', exc_info=True)
                    return self._finalize_consume(param, value, found, e)

    def _finalize_consume(
        self, param: Parameter, value: Optional[str], found: int, exc: Optional[Exception] = None
    ) -> int:
        if param.nargs.satisfied(found):
            if value is not None:
                self.arg_deque.appendleft(value)
            # log.debug(f'consume_values {found=} for {param=}')
            return found
        elif exc:
            raise exc
        else:
            raise MissingArgument(param, f'expected {param.nargs.min} values, but only found {found}')
