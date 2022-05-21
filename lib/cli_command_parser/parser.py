"""
:author: Doug Skrypa
"""

import logging
from collections import deque
from typing import TYPE_CHECKING, Optional, Any, Deque

from .actions import help_action
from .context import ctx
from .exceptions import (
    UsageError,
    NoSuchOption,
    MissingArgument,
    ParamUsageError,
    CommandDefinitionError,
    ParamsMissing,
)
from .parameters import BaseOption, Parameter, BasePositional

if TYPE_CHECKING:
    from .core import CommandType

__all__ = ['CommandParser']
log = logging.getLogger(__name__)


class CommandParser:
    """Stateful parser used for a single pass of argument parsing"""

    def __init__(self):
        self.params = ctx.params
        self.deferred = None
        self.arg_deque = None
        self.positionals = ctx.params.positionals.copy()

    @classmethod
    def parse_args(cls) -> Optional['CommandType']:
        params = ctx.params
        sub_cmd_param = params.sub_command
        if sub_cmd_param is not None and not sub_cmd_param.choices:
            raise CommandDefinitionError(f'{ctx.command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        cls()._parse_args()
        for group in params.groups:
            group.validate()

        if sub_cmd_param is not None:
            try:
                next_cmd = sub_cmd_param.result()  # type: CommandType
            except UsageError:
                if help_action not in ctx:
                    raise
            else:
                missing = params.missing()
                if missing and next_cmd.__class__.parent(next_cmd) is not ctx.command:
                    if help_action in ctx:
                        return None
                    raise ParamsMissing(missing)
                return next_cmd

        missing = params.missing()
        if missing and not ctx.allow_missing and (not params.action or params.action not in missing):
            # Action is excluded because it provides a better error message
            if help_action not in ctx:
                raise ParamsMissing(missing)
        elif ctx.remaining and not ctx.ignore_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(ctx.remaining)))

        return None

    def _parse_args(self):
        self.arg_deque = arg_deque = self.handle_pass_thru()
        self.deferred = ctx.remaining = []
        while arg_deque:
            arg = arg_deque.popleft()
            if arg == '--':
                if ctx.params.find_nested_pass_thru():
                    self.deferred.append(arg)
                    self.deferred.extend(arg_deque)
                    break
                else:
                    raise NoSuchOption(f'invalid argument: {arg}')
            elif arg.startswith('---'):
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

    def handle_pass_thru(self) -> Deque[str]:
        remaining = ctx.remaining
        pass_thru = self.params.pass_thru
        if pass_thru is not None:
            try:
                separator_pos = remaining.index('--')
            except ValueError as e:
                if pass_thru.required:
                    raise MissingArgument(pass_thru, "missing pass thru args separated from others with '--'") from e
            else:
                remainder_start = separator_pos + 1
                pass_thru.take_action(remaining[remainder_start:])
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
                found = param.take_action(arg)
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
                param.take_action(value)
            elif not self.consume_values(param) and param.accepts_none:
                param.take_action(None)

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
                param.take_action(None, short_combo=True)

            self._handle_short_value(last, None)

    def _handle_short_value(self, param: BaseOption, value: Any):
        # log.debug(f'Handling short {value=} for {param=}')
        if value is not None or (param.accepts_none and not param.accepts_values):
            param.take_action(value, short_combo=True)
        elif not self.consume_values(param) and param.accepts_none:
            param.take_action(None, short_combo=True)
        # No need to raise MissingArgument if values were not consumed - consume_values handles checking nargs

    def _check_sub_command_options(self, arg: str):
        # log.debug(f'_check_sub_command_options({arg=})')
        # This check is only needed when subcommand option values may be misinterpreted as positional values
        if not self.positionals:
            return
        param = self.params.find_nested_option_that_accepts_values(arg)
        if param is not None:
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

                    if not param.would_accept(value):
                        # log.debug(f'{value=} will not be used with {param=} - it would not be accepted')
                        return self._finalize_consume(param, value, found, NoSuchOption(f'invalid argument: {value}'))
                    # log.debug(f'{value=} may be used with {param=} as a value')

                try:
                    found += param.take_action(value)
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
