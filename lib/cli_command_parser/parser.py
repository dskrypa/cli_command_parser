"""
The class that handles parsing input.

:author: Doug Skrypa
"""

from __future__ import annotations

# import logging
from collections import deque
from os import environ
from typing import TYPE_CHECKING, Optional, Union, Any, Deque, List

from .context import ActionPhase, Context
from .exceptions import UsageError, ParamUsageError, NoSuchOption, MissingArgument, ParamsMissing
from .exceptions import Backtrack, UnsupportedAction
from .nargs import REMAINDER, nargs_max_sum, nargs_min_sum
from .parse_tree import PosNode
from .parameters.base import BasicActionMixin, Parameter, BasePositional, BaseOption

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .config import CommandConfig
    from .typing import CommandType

__all__ = ['CommandParser']
# log = logging.getLogger(__name__)


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
        no_pre_init_action = not ctx.categorized_action_flags[ActionPhase.PRE_INIT]
        next_cmd = params.sub_command.target() if params.sub_command else None
        if next_cmd is not None:
            if missing and no_pre_init_action and next_cmd.__class__.parent(next_cmd) is not ctx.command:
                raise ParamsMissing(missing)
        elif missing and not ctx.config.allow_missing and (not params.action or params.action not in missing):
            if no_pre_init_action:
                raise ParamsMissing(missing)
        elif ctx.remaining and not ctx.config.ignore_unknown:
            raise NoSuchOption(f'unrecognized arguments: {" ".join(ctx.remaining)}') from None
        return next_cmd

    def _parse_args(self, ctx: Context):
        self.arg_deque = arg_deque = self.handle_pass_thru(ctx)
        self.deferred = ctx.remaining = []
        while arg_deque:
            arg = arg_deque.popleft()
            try:
                if self._parse_arg(ctx, arg):
                    break
            except NextCommand:
                self.deferred.append(arg)
                self.deferred.extend(arg_deque)
                break

        self._parse_env_vars(ctx)

    def _parse_arg(self, ctx: Context, arg: str):
        if arg == '--':
            if self._maybe_consume_remainder(arg):
                return True
            elif ctx.params.find_nested_pass_thru():  # pylint: disable=R1723
                # TODO: Make sure a test exists where parsing fails because required params were not provided yet
                raise NextCommand
            else:
                raise NoSuchOption(f'invalid argument: {arg}')
        elif arg.startswith('---'):
            if not self._maybe_consume_remainder(arg):
                raise NoSuchOption(f'invalid argument: {arg}')
        elif arg.startswith('--'):
            self.handle_long(arg)
        elif arg.startswith('-') and arg != '-':
            self.handle_short(arg)
        else:
            self.handle_positional(arg)

        return False

    def _parse_env_vars(self, ctx: Context):
        # TODO: It would be helpful to store arg provenance for error messages, especially for a conflict between
        #  mutually exclusive params when they were provided via env
        for param in self.params.try_env_params(ctx):
            for env_var in param.env_vars():
                try:
                    value = environ[env_var]
                except KeyError:
                    pass
                else:
                    param.take_action(value)
                    break

    def handle_pass_thru(self, ctx: Context) -> Deque[str]:
        remaining = ctx.remaining
        pass_thru = self.params.pass_thru
        if pass_thru is not None:
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

    def handle_positional(self, arg: str):
        # log.debug(f'handle_positional({arg=})')
        try:
            param: BasePositional = self.positionals.pop(0)
        except IndexError:
            self.deferred.append(arg)
        else:
            if param.nargs.max is REMAINDER:
                self.handle_remainder(param, arg)
            else:
                try:
                    found = param.take_action(arg)
                except UsageError:
                    self.positionals.insert(0, param)
                    raise
                try:
                    self.consume_values(param, found=found)
                except Backtrack:
                    self.positionals.insert(0, param)
                else:
                    self._last = param

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

    def handle_short(self, arg: str):
        # log.debug(f'handle_short({arg=})')
        try:
            param_val_combos = self.params.short_option_to_param_value_pairs(arg)
        except KeyError:
            self._handle_short_not_found(arg)
        else:
            # log.debug(f'Split {arg=} into {param_val_combos=}')
            if len(param_val_combos) == 1:
                opt, param, value = param_val_combos[0]
                self._handle_short_value(opt, param, value)
            else:
                last_opt, last_param, _last_val = param_val_combos[-1]
                for opt, param, _ in param_val_combos[:-1]:
                    param.take_action(None, short_combo=True, opt_str=opt)

                self._handle_short_value(last_opt, last_param, None)

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

    def _check_sub_command_options(self, arg: str):
        # log.debug(f'_check_sub_command_options({arg=})')
        # This check is only needed when subcommand option values may be misinterpreted as positional values
        if not self.positionals:
            return
        param = self.params.find_nested_option_that_accepts_values(arg)
        if param is None:
            return
        elif len(self.positionals) == 1 and 0 in self.positionals[0].nargs:
            raise NextCommand
        else:
            raise ParamUsageError(param, 'subcommand arguments must be provided after the subcommand')

    def _maybe_backtrack(self, param: Parameter, found: int) -> int:
        """
        If we hit the end of the list of provided argument values, unfulfilled Positional parameters remain, and the
        Parameter being processed accepts a variable number of arguments, then check to see if it's possible to
        backtrack to move some of those values to the remaining positionals.

        :param param: The :class:`.Parameter` that was consuming values when the arg_deque became empty
        :param found: The number of values that were consumed by the given Parameter
        :return: The updated found count, if backtracking was possible, otherwise the unmodified found count
        """
        if not self.config.allow_backtrack or not self.positionals or found < 2:
            return found

        can_pop = param.can_pop_counts()
        to_pop = _to_pop(self.positionals, can_pop, found - 1)
        if to_pop is None:
            return found

        self.arg_deque.extendleft(reversed(param.pop_last(to_pop)))
        return found - to_pop

    def _maybe_backtrack_last(self, param: Union[BasePositional, BasicActionMixin], found: int):
        """
        Similar to :meth:`._maybe_backtrack`, but allows backtracking even after starting to process a Positional.
        """
        if not self.config.allow_backtrack:
            return

        can_pop = self._last.can_pop_counts()
        to_pop = _to_pop([param, *self.positionals], can_pop, max(can_pop, default=0) + found, found)
        if to_pop is None:
            return

        try:
            reset = param._reset()
        except UnsupportedAction:
            return

        self.arg_deque.extendleft(reversed(reset))
        self.arg_deque.extendleft(reversed(self._last.pop_last(to_pop)))
        raise Backtrack

    def consume_values(self, param: Parameter, found: int = 0) -> int:
        """
        Consume values for the given Parameter.

        :param param: The active :class:`.Parameter` that should receive the discovered values
        :param found: The number of already discovered values for that Parameter (only specified for positional params)
        :return: The total number of values that were found for the given Parameter.
        """
        remainder = param.nargs.max is REMAINDER
        while True:
            try:
                value = self.arg_deque.popleft()
            except IndexError:
                # log.debug(f'Ran out of values in deque while processing {param=}')
                found = self._maybe_backtrack(param, found)
                return self._finalize_consume(param, None, found)
            else:
                # log.debug(f'Found {value=} in deque - may use it for {param=}')
                if remainder:
                    return self.handle_remainder(param, value)
                elif value.startswith('--'):
                    return self._finalize_consume(param, value, found)
                elif value.startswith('-') and value != '-':
                    if self.params.get_option_param_value_pairs(value):
                        # log.debug(f'{value=} will not be used with {param=} - it is also a parameter')
                        return self._finalize_consume(param, value, found)
                    else:
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

    def _finalize_consume(
        self, param: Parameter, value: Optional[str], found: int, exc: Optional[Exception] = None
    ) -> int:
        if param.nargs.satisfied(found):
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

        n = param.nargs.min
        s = '' if n == 1 else 's'
        raise MissingArgument(param, f'expected {n} value{s}, but only found {found}')


def _to_pop(positionals: List[BasePositional], can_pop: List[int], available: int, req_mod: int = 0) -> Optional[int]:
    if not can_pop:
        return None

    required = nargs_min_sum(p.nargs for p in positionals)
    if available < required:
        return None

    required -= req_mod
    acceptable = nargs_max_sum(p.nargs for p in positionals)
    for n in can_pop:
        if required <= n <= acceptable:
            return n

    return None


class NextCommand(Exception):
    pass
