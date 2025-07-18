"""
The class that handles parsing input.

:author: Doug Skrypa
"""

from __future__ import annotations

import logging
from collections import deque
from os import environ
from typing import TYPE_CHECKING, Deque, Sequence

from .context import ActionPhase, Context
from .core import get_parent
from .exceptions import (
    Backtrack,
    MissingArgument,
    NextCommand,
    NoSuchOption,
    ParamsMissing,
    ParamUsageError,
    UsageError,
)
from .nargs import REMAINDER
from .parameters.base import BaseOption, BasePositional, Parameter
from .parse_tree import PosNode

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .config import CommandConfig
    from .typing import Bool, CommandType, OptStr

__all__ = ['CommandParser', 'parse_args_and_get_next_cmd']
log = logging.getLogger(__name__)

_PRE_INIT = ActionPhase.PRE_INIT

# TODO: When an invalid choice for a positional is provided with -h / --help, the invalid choice error is shown instead
#  of help, but help should be shown instead


class CommandParser:
    """Stateful parser used for a single pass of argument parsing"""

    __slots__ = ('_last', 'arg_deque', 'ctx', 'config', 'deferred', 'params', 'positionals')

    arg_deque: Deque[str] | None
    config: CommandConfig
    deferred: list[str] | None
    params: CommandParameters
    positionals: list[BasePositional]
    _last: Parameter | None

    def __init__(self, ctx: Context, params: CommandParameters, config: CommandConfig):
        self._last = None
        self.ctx = ctx
        self.params = params
        self.positionals = params.get_positionals_to_parse(ctx)
        self.config = config
        if config.reject_ambiguous_pos_combos:
            PosNode.build_tree(ctx.command_cls)

    @classmethod
    def parse_args_and_get_next_cmd(cls, ctx: Context) -> CommandType | None:
        try:
            return cls(ctx, ctx.params, ctx.config).get_next_cmd(ctx)
        except UsageError:
            if not ctx.categorized_action_flags[_PRE_INIT]:
                raise
            return None

    def get_next_cmd(self, ctx: Context) -> CommandType | None:
        self._parse_args(ctx)
        self._validate_groups()
        missing = ctx.get_missing()
        if self.params.sub_command and (next_cmd := self.params.sub_command.target()) is not None:
            if missing and not ctx.categorized_action_flags[_PRE_INIT] and get_parent(next_cmd) is not ctx.command_cls:
                raise ParamsMissing(missing)
            return next_cmd
        elif missing and not ctx.config.allow_missing and (not self.params.action or self.params.action not in missing):
            if not ctx.categorized_action_flags[_PRE_INIT]:  # No pre-init action was triggered
                raise ParamsMissing(missing)
        elif ctx.remaining and not ctx.config.ignore_unknown:  # Note: ctx.remaining is self.deferred at this point
            raise NoSuchOption(f'unrecognized arguments: {" ".join(ctx.remaining)}') from None
        return None

    def _validate_groups(self):
        exc = None
        for group in self.params.groups:
            try:
                group.validate()
            except ParamsMissing as e:  # Let ParamConflict propagate before ParamsMissing
                if exc is None:
                    exc = e

        if exc is not None:
            raise exc

    def _parse_args(self, ctx: Context):
        self.arg_deque = arg_deque = self.handle_pass_thru(ctx)
        self.deferred = ctx.remaining = []

        while arg_deque:
            arg = arg_deque.popleft()
            try:
                if self._handle_arg(arg):
                    break
            except NextCommand:
                self.deferred.append(arg)
                self.deferred.extend(arg_deque)
                break

        self._parse_env_vars(ctx)

    def _parse_env_vars(self, ctx: Context):
        for param in ctx.missing_options_with_env_var():
            for env_var in param.env_vars():
                try:
                    value = environ[env_var]
                except KeyError:
                    pass
                else:
                    try:
                        param.action.add_env_value(value, env_var)
                    except ParamUsageError as e:
                        if param.strict_env:
                            raise
                        log.warning(e)
                    break

    def _handle_arg(self, arg: str):
        if not arg or arg[0] != '-':
            return self.handle_positional(arg)
        n = len(arg)
        if n > 1 and arg[1] != '-':  # arg starts with 1 dash followed by a non-dash
            return self.handle_short(arg)
        elif n > 2:  # arg starts with at least 1 dash, and may be a long option or invalid
            return self.handle_long(arg) if arg[2] != '-' else self._handle_many_dashes(arg)
        else:  # arg == '--'
            return self._handle_double_dash(arg)

    def _handle_double_dash(self, arg: str):
        if self._maybe_consume_remainder(arg):
            return True
        elif self.params.has_nested_pass_thru:  # pylint: disable=R1723
            # TODO: Make sure a test exists where parsing fails because required params were not provided yet
            raise NextCommand
        else:
            raise NoSuchOption(f'invalid argument: {arg}')

    def _handle_many_dashes(self, arg: str):
        if not self._maybe_consume_remainder(arg):
            raise NoSuchOption(f'invalid argument: {arg}')

    # region PassThru / Remainder Handling

    def handle_pass_thru(self, ctx: Context) -> Deque[str]:
        remaining = ctx.remaining
        if pass_thru := self.params.pass_thru:
            try:
                separator_pos = remaining.index('--')
            except ValueError:
                pass  # If required, it's handled by the normal missing param handler
            else:
                remainder_start = separator_pos + 1
                pass_thru.action.add_values(remaining[remainder_start:])
                return deque(remaining[:separator_pos])
        return deque(remaining)

    def _maybe_consume_remainder(self, arg: str) -> bool:
        if len(self.positionals) == 1:
            param = self.positionals[0]
            if param.nargs.max is REMAINDER:
                self.handle_remainder(param, arg)
                return True
        return False

    def handle_remainder(self, param: Parameter, value: str) -> int:
        found = param.action.add_value(value)
        arg_deque = self.arg_deque
        while arg_deque:
            found += param.action.add_value(arg_deque.popleft())
        return found

    # endregion

    def handle_positional(self, arg: str):
        # log.debug(f'handle_positional({arg=})')
        if self.positionals:
            param: BasePositional = self.positionals.pop(0)
            if param.nargs.max is REMAINDER:
                self.handle_remainder(param, arg)
            else:
                try:
                    found = param.action.add_value(arg)
                except UsageError:
                    self.positionals.insert(0, param)
                    raise
                try:
                    self.consume_values(param, found=found)
                except Backtrack:
                    self.positionals.insert(0, param)
                else:
                    self._last = param
        else:
            self.deferred.append(arg)

    # region Option Handling

    def handle_long(self, arg: str):
        # log.debug(f'handle_long({arg=})')
        opt, eq, value = arg.partition('=')
        if param := self.params.option_map.get(opt):
            self._handle_option_value(opt, param, value if eq else None, joined=eq)
        elif not self._maybe_consume_remainder(arg):
            self._check_sub_command_options(arg)
            self.deferred.append(arg)

    def _handle_option_value(
        self, opt: str, param: BaseOption, value: OptStr, combo: bool = False, joined: Bool = False
    ):
        if value is not None:
            param.action.add_value(value, combo=combo, joined=joined)
        elif param.action.accepts_consts and not param.action.accepts_values:
            param.action.add_const(opt=opt, combo=combo)
        elif not self.consume_values(param) and param.action.accepts_consts:
            # The order of conditions here is important - consume_values has an intended side effect even when
            # the action does not accept constants
            param.action.add_const(opt=opt, combo=combo)

        self._last = param
        # No need to raise MissingArgument if values were not consumed - consume_values handles checking nargs

    def handle_short(self, arg: str):
        # log.debug(f'handle_short({arg=})')
        try:
            param_val_combos, joined = self.params.short_option_to_param_value_pairs(arg)
        except KeyError:  # Handles 3 potential KeyErrors for either the full short option or a single-char combo
            self._handle_short_not_found(arg)
        else:
            # log.debug(f'Split {arg=} into {param_val_combos=}')
            last = param_val_combos.pop()
            if param_val_combos:
                # Note: This loop is only executed for single char combined flags, where the values will always be None
                for opt, param, _none_value in param_val_combos:
                    param.action.add_const(opt=opt, combo=True)
            self._handle_option_value(*last, combo=True, joined=joined)

    def _handle_short_not_found(self, arg: str):
        if self._maybe_consume_remainder(arg):
            return
        self._check_sub_command_options(arg)
        if self.positionals:
            try:
                self.handle_positional(arg)
            except UsageError:
                self.deferred.append(arg)
        else:
            self.deferred.append(arg)

    # endregion

    def _check_sub_command_options(self, arg: str):
        # log.debug(f'_check_sub_command_options({arg=})')
        # This check is only needed when subcommand option values may be misinterpreted as positional values
        if not self.positionals:
            return
        option = arg.split('=', 1)[0]  # Strip any `=value` suffix if it exists
        ncps = self.params._iter_nested_params()
        # Try to find a nested Option that accepts values
        if param := next((p for cp in ncps if (p := cp.option_map.get(option)) and p.action.accepts_values), None):
            if len(self.positionals) == 1 and 0 in self.positionals[0].nargs:
                raise NextCommand
            else:
                raise ParamUsageError(param, 'subcommand arguments must be provided after the subcommand')  # noqa

    # region Backtracking

    def _maybe_backtrack(self, param: Parameter, found: int) -> int:
        """
        If we hit the end of the list of provided argument values, unfulfilled Positional parameters remain, and the
        Parameter being processed accepts a variable number of arguments, then check to see if it's possible to
        backtrack to move some of those values to the remaining positionals.

        :param param: The :class:`.Parameter` that was consuming values when the arg_deque became empty
        :param found: The number of values that were consumed by the given Parameter
        :return: The updated found count, if backtracking was possible, otherwise the unmodified found count
        """
        if not self.positionals:
            return found
        elif rollback_count := self._get_backtrack_count(param):
            self.arg_deque.extendleft(reversed(self.ctx.roll_back_parsed_values(param, rollback_count)))
            return found - rollback_count
        else:
            return found

    def _get_backtrack_count(
        self, param: Parameter, extras: Sequence[str] = (), positionals: Sequence[BasePositional] = ()
    ) -> int:
        if poppable_groups := param.action.get_maybe_poppable_values():
            return next((len(g) for g in poppable_groups if self._should_backtrack(g, extras, positionals)), 0)
        return 0

    def _should_backtrack(
        self, group: list[str], extras: Sequence[str] = (), positionals: Sequence[BasePositional] = ()
    ) -> bool:
        args = [*group, *extras, *self.arg_deque]
        for pos_param in positionals or self.positionals:
            n = pos_param.nargs.min
            if not n and 1 in pos_param.nargs:
                n = 1

            param_args = args[:n]
            if len(param_args) != n or not pos_param.action.would_accept_all(param_args):
                return False

            args = args[n:]

        return True

    def _maybe_backtrack_last_positional(self, param: BasePositional):
        """
        Similar to :meth:`._maybe_backtrack`, but allows backtracking even after starting to process a Positional.

        By the time this method is called, it has already been discovered that `found` does not satisfy `param`'s
        nargs requirements.
        """
        if not self.config.allow_backtrack:
            # This method is called extremely rarely & it's cleaner to have this check here than in _finalize_consume
            return

        parsed = self.ctx.get_parsed_value(param, ())
        # It is extremely unlikely for this point to be reached without this resulting in triggering backtrack
        if num := self._get_backtrack_count(self._last, parsed, (param, *self.positionals)):
            # log.debug(f'Rolling back {num} parsed values from {self._last=} / {param=} and triggering Backtrack')
            # Reset all of this param's parsed args because the previous param's roll back args need to be injected
            # before them so they can be processed by this parameter.
            self.arg_deque.extendleft(reversed(self.ctx.pop_parsed_value(param)))
            # Roll back a subset of the previous param's parsed args
            self.arg_deque.extendleft(reversed(self.ctx.roll_back_parsed_values(self._last, num)))
            raise Backtrack

    # endregion

    def _has_matching_short_option(self, arg: str) -> bool:
        try:
            self.params.short_option_to_param_value_pairs(arg)
        except KeyError:
            return False
        return True

    def consume_values(self, param: Parameter, found: int = 0) -> int:
        """
        Consume values for the given Parameter.

        :param param: The active :class:`.Parameter` that should receive the discovered values
        :param found: The number of already discovered values for that Parameter (only specified for positional params)
        :return: The total number of values that were found for the given Parameter.
        """
        arg_deque = self.arg_deque
        if param.nargs.max is REMAINDER and arg_deque:
            return self.handle_remainder(param, arg_deque.popleft())

        while arg_deque:
            value = arg_deque.popleft()
            # log.debug(f'Found {value=} in deque - may use it for {param=}')
            if prefix := get_opt_prefix(value):
                if prefix == '--' or self._has_matching_short_option(value):
                    return self._finalize_consume(param, value, found)
                # Beyond this point, prefix == '-'
                try:
                    self._check_sub_command_options(value)
                except (ParamUsageError, NextCommand) as e:
                    return self._finalize_consume(param, value, found, e)

                if not param.action.would_accept(value):
                    # log.debug(f'{value=} will not be used with {param=} - it would not be accepted')
                    return self._finalize_consume(param, value, found, NoSuchOption(f'invalid argument: {value}'))
                # log.debug(f'{value=} may be used with {param=} as a value')

            try:
                found += param.action.add_value(value)
            except UsageError as e:
                # log.debug(f'{value=} was rejected by {param=}', exc_info=True)
                return self._finalize_consume(param, value, found, e)

        # log.debug(f'Ran out of values in deque while processing {param=}')
        if found >= 2 and self.config.allow_backtrack:
            found = self._maybe_backtrack(param, found)
        return self._finalize_consume(param, None, found)

    def _finalize_consume(self, param: Parameter, value: OptStr, found: int, exc: Exception | None = None) -> int:
        # log.debug(f'Finalizing arg consumption for {param=}, {value=}, {found=}, {exc=}')
        nargs = param.nargs
        if nargs.satisfied(found):
            # Even if an exception was passed to this method, if the found number of values is acceptable, then it
            # doesn't need to be raised.  The value that (would have) caused the exception is added back to the deque.
            if value is not None:
                self.arg_deque.appendleft(value)
            # log.debug(f'consume_values {found=} for {param=}')
            return found
        elif exc:
            raise exc
        elif self._last and isinstance(param, BasePositional) and param.action.can_reset():
            self._maybe_backtrack_last_positional(param)

        s = '' if nargs.min == 1 else 's'
        raise MissingArgument(param, f'expected {nargs.min} value{s}, but only found {found}')


parse_args_and_get_next_cmd = CommandParser.parse_args_and_get_next_cmd


def get_opt_prefix(text: str) -> OptStr:
    if not text or text[0] != '-':
        return None
    n = len(text)
    if n > 1 and text[1] != '-':
        return '-'
    elif n > 2 and text[2] != '-':
        return '--'
    return None
