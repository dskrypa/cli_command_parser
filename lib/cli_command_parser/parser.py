"""
The class that handles parsing input.

:author: Doug Skrypa
"""

from __future__ import annotations

# import logging
from collections import deque
from os import environ
from typing import TYPE_CHECKING, Optional, Union, Any, Iterable, Deque, List

from .core import get_parent
from .context import ActionPhase, Context
from .exceptions import UsageError, ParamUsageError, NoSuchOption, MissingArgument, ParamsMissing
from .exceptions import Backtrack, NextCommand, UnsupportedAction
from .nargs import REMAINDER, nargs_min_and_max_sums
from .parse_tree import PosNode
from .parameters.base import BasicActionMixin, Parameter, BasePositional, BaseOption
from .utils import ValueSource

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .config import CommandConfig
    from .typing import CommandType, OptStr

__all__ = ['CommandParser']
# log = logging.getLogger(__name__)

_PRE_INIT = ActionPhase.PRE_INIT


class CommandParser:
    """Stateful parser used for a single pass of argument parsing"""

    __slots__ = ('_last', 'arg_deque', 'config', 'deferred', 'params', 'positionals')

    arg_deque: Optional[Deque[str]]
    config: CommandConfig
    deferred: Optional[List[str]]
    params: CommandParameters
    positionals: List[BasePositional]
    _last: Optional[Parameter]

    def __init__(self, ctx: Context, params: CommandParameters, config: CommandConfig):
        self._last = None
        self.params = params
        self.positionals = params.get_positionals_to_parse(ctx)
        self.config = config
        if config.reject_ambiguous_pos_combos:
            PosNode.build_tree(ctx.command)

    @classmethod
    def parse_args_and_get_next_cmd(cls, ctx: Context) -> Optional[CommandType]:
        try:
            return cls(ctx, ctx.params, ctx.config).get_next_cmd(ctx)
        except UsageError:
            if not ctx.categorized_action_flags[ActionPhase.PRE_INIT]:
                raise
            return None

    def get_next_cmd(self, ctx: Context) -> Optional[CommandType]:
        self._parse_args(ctx)
        params = self.params
        params.validate_groups()
        missing = ctx.get_missing()
        if (sub_cmd_param := params.sub_command) and (next_cmd := sub_cmd_param.target()) is not None:
            if missing and not ctx.categorized_action_flags[_PRE_INIT] and get_parent(next_cmd) is not ctx.command:
                raise ParamsMissing(missing)
            return next_cmd
        elif missing and not ctx.config.allow_missing and (not params.action or params.action not in missing):
            if not ctx.categorized_action_flags[_PRE_INIT]:  # No pre-init action was triggered
                raise ParamsMissing(missing)
        elif ctx.remaining and not ctx.config.ignore_unknown:  # Note: ctx.remaining is self.deferred at this point
            raise NoSuchOption(f'unrecognized arguments: {" ".join(ctx.remaining)}') from None
        return None

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
        # TODO: It would be helpful to store arg provenance for error messages, especially for a conflict between
        #  mutually exclusive params when they were provided via env
        env = ValueSource.ENV
        for param in self.params.try_env_params(ctx):
            for env_var in param.env_vars():
                try:
                    value = environ[env_var]
                except KeyError:
                    pass
                else:
                    param.take_action(value, src=(env, env_var))
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
        elif self.params.find_nested_pass_thru():  # pylint: disable=R1723
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
                pass_thru.take_action(remaining[remainder_start:])
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
        found = param.take_action(value)
        arg_deque = self.arg_deque
        while arg_deque:
            found += param.take_action(arg_deque.popleft())
        return found

    # endregion

    def handle_positional(self, arg: str):
        # log.debug(f'handle_positional({arg=})')
        if positionals := self.positionals:
            param: BasePositional = positionals.pop(0)
            if param.nargs.max is REMAINDER:
                self.handle_remainder(param, arg)
            else:
                try:
                    found = param.take_action(arg)
                except UsageError:
                    positionals.insert(0, param)
                    raise
                try:
                    self.consume_values(param, found=found)
                except Backtrack:
                    positionals.insert(0, param)
                else:
                    self._last = param
        else:
            self.deferred.append(arg)

    def handle_long(self, arg: str):
        # log.debug(f'handle_long({arg=})')
        try:
            opt, param, value = self.params.long_option_to_param_value_pair(arg)
        except KeyError:
            if not self._maybe_consume_remainder(arg):
                self._check_sub_command_options(arg)
                self.deferred.append(arg)
        else:
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(value, opt_str=opt)
            elif not self.consume_values(param) and param.accepts_none:
                param.take_action(None, opt_str=opt)
            self._last = param

    # region Short Option Handling

    def handle_short(self, arg: str):
        # log.debug(f'handle_short({arg=})')
        try:
            param_val_combos = self.params.short_option_to_param_value_pairs(arg)
        except KeyError:  # Handles 3 potential KeyErrors for either the full short option or a single-char combo
            self._handle_short_not_found(arg)
        else:
            # log.debug(f'Split {arg=} into {param_val_combos=}')
            last = param_val_combos.pop()
            if param_val_combos:
                # Note: This loop is only executed for single char combined flags, where the values will always be None
                for opt, param, none_value in param_val_combos:
                    param.take_action(none_value, short_combo=True, opt_str=opt)
            self._handle_short_value(*last)

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

    def _handle_short_value(self, opt: str, param: BaseOption, value: Any):
        # log.debug(f'Handling short {value=} for {param=}')
        if value is not None or (param.accepts_none and not param.accepts_values):
            param.take_action(value, short_combo=True, opt_str=opt)
        elif not self.consume_values(param) and param.accepts_none:
            param.take_action(None, short_combo=True, opt_str=opt)
        self._last = param
        # No need to raise MissingArgument if values were not consumed - consume_values handles checking nargs

    # endregion

    def _check_sub_command_options(self, arg: str):
        # log.debug(f'_check_sub_command_options({arg=})')
        # This check is only needed when subcommand option values may be misinterpreted as positional values
        if (positionals := self.positionals) and (param := self.params.find_nested_option_that_accepts_values(arg)):
            if len(positionals) == 1 and 0 in positionals[0].nargs:
                raise NextCommand
            else:
                raise ParamUsageError(param, 'subcommand arguments must be provided after the subcommand')

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
        if (positionals := self.positionals) and (to_pop := _to_pop(positionals, param.can_pop_counts(), found - 1)):
            self.arg_deque.extendleft(reversed(param.pop_last(to_pop)))
            return found - to_pop
        else:
            return found

    def _maybe_backtrack_last(self, param: Union[BasePositional, BasicActionMixin], found: int):
        """
        Similar to :meth:`._maybe_backtrack`, but allows backtracking even after starting to process a Positional.
        """
        if not self.config.allow_backtrack:
            return

        can_pop = self._last.can_pop_counts()
        if to_pop := _to_pop((param, *self.positionals), can_pop, max(can_pop, default=0) + found, found):
            try:
                reset = param._reset()
            except UnsupportedAction:
                return

            self.arg_deque.extendleft(reversed(reset))
            self.arg_deque.extendleft(reversed(self._last.pop_last(to_pop)))
            raise Backtrack
        else:
            return

    # endregion

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
                if prefix == '--' or self.params.has_matching_short_option(value):
                    return self._finalize_consume(param, value, found)
                # Beyond this point, prefix == '-'
                try:
                    self._check_sub_command_options(value)
                except (ParamUsageError, NextCommand) as e:
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

        # log.debug(f'Ran out of values in deque while processing {param=}')
        if found >= 2 and self.config.allow_backtrack:
            found = self._maybe_backtrack(param, found)
        return self._finalize_consume(param, None, found)

    def _finalize_consume(self, param: Parameter, value: OptStr, found: int, exc: Optional[Exception] = None) -> int:
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
        elif self._last and isinstance(param, BasePositional) and hasattr(param, '_reset'):
            self._maybe_backtrack_last(param, found)

        s = '' if (n := nargs.min) == 1 else 's'
        raise MissingArgument(param, f'expected {n} value{s}, but only found {found}')


def _to_pop(positionals: Iterable[BasePositional], can_pop: List[int], available: int, req_mod: int = 0) -> int:
    if not can_pop:
        return 0

    required, acceptable = nargs_min_and_max_sums(p.nargs for p in positionals)
    if available < required:
        return 0

    required -= req_mod
    for n in can_pop:
        if required <= n <= acceptable:
            return n

    return 0


def get_opt_prefix(text: str) -> OptStr:
    if not text or text[0] != '-':
        return None
    n = len(text)
    if n > 1 and text[1] != '-':
        return '-'
    elif n > 2 and text[2] != '-':
        return '--'
    return None
