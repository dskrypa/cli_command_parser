"""
The class that handles parsing input.

:author: Doug Skrypa
"""

from __future__ import annotations

# import logging
from collections import deque
from typing import TYPE_CHECKING, Optional, Union, Any, Deque, List

from .context import ActionPhase, Context
from .exceptions import UsageError, ParamUsageError, NoSuchOption, MissingArgument, ParamsMissing
from .exceptions import CommandDefinitionError, Backtrack, UnsupportedAction
from .parameters.base import BasicActionMixin, Parameter, BasePositional, BaseOption

if TYPE_CHECKING:
    from .core import CommandType
    from .command_parameters import CommandParameters

__all__ = ['CommandParser']
# log = logging.getLogger(__name__)


class CommandParser:
    """Stateful parser used for a single pass of argument parsing"""

    arg_deque: Optional[Deque[str]] = None
    deferred: Optional[List[str]] = None
    _last: Optional[Parameter] = None

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.params = ctx.params
        self.positionals = ctx.params.positionals.copy()

    @classmethod
    def parse_args(cls, ctx: Context) -> Optional[CommandType]:
        try:
            return cls.__parse_args(ctx)
        except UsageError:
            ctx.failed = True
            if not ctx.categorized_action_flags[ActionPhase.PRE_INIT]:
                raise
            return None
        except Exception:
            ctx.failed = True
            raise

    @classmethod
    def __parse_args(cls, ctx: Context) -> Optional[CommandType]:
        params = ctx.params
        sub_cmd_param = params.sub_command
        if sub_cmd_param is not None and not sub_cmd_param.choices:
            raise CommandDefinitionError(f'{ctx.command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        cls(ctx)._parse_args(ctx)
        cls._validate_groups(params)

        if sub_cmd_param is not None:
            next_cmd = sub_cmd_param.target()  # type: CommandType
            missing = cls._missing(params, ctx)
            if missing and next_cmd.__class__.parent(next_cmd) is not ctx.command:
                ctx.failed = True
                if ctx.categorized_action_flags[ActionPhase.PRE_INIT]:
                    return None
                raise ParamsMissing(missing)
            return next_cmd

        missing = cls._missing(params, ctx)
        if missing and not ctx.config.allow_missing and (not params.action or params.action not in missing):
            # Action is excluded because it provides a better error message
            if not ctx.categorized_action_flags[ActionPhase.PRE_INIT]:
                raise ParamsMissing(missing)
        elif ctx.remaining and not ctx.config.ignore_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(ctx.remaining)))

        return None

    @classmethod
    def _missing(cls, params: CommandParameters, ctx: Context) -> List[Parameter]:
        return [p for p in params.required_check_params() if p.required and ctx.num_provided(p) == 0]

    @classmethod
    def _validate_groups(cls, params: CommandParameters):
        exc = None
        for group in params.groups:
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
            if arg == '--':
                if ctx.params.find_nested_pass_thru():  # pylint: disable=R1723
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
        param_val_combos = self.params.short_option_to_param_value_pairs(arg)
        # log.debug(f'Split {arg=} into {param_val_combos=}')
        if len(param_val_combos) == 1:
            opt, param, value = param_val_combos[0]
            self._handle_short_value(opt, param, value)
        else:
            last_opt, last_param, _last_val = param_val_combos[-1]
            for opt, param, _ in param_val_combos[:-1]:
                param.take_action(None, short_combo=True, opt_str=opt)

            self._handle_short_value(last_opt, last_param, None)

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
        if param is not None:
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
        if not self.ctx.config.allow_backtrack or not self.positionals or found < 2:
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
        if not self.ctx.config.allow_backtrack:
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
        while True:
            try:
                value = self.arg_deque.popleft()
            except IndexError:
                # log.debug(f'Ran out of values in deque while processing {param=}')
                found = self._maybe_backtrack(param, found)
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

    required = sum(p.nargs.min for p in positionals)
    if available < required:
        return None

    required -= req_mod
    nargs_max_vals = [p.nargs.max for p in positionals]
    acceptable = float('inf') if None in nargs_max_vals else sum(nargs_max_vals)
    for n in can_pop:
        if required <= n <= acceptable:
            return n

    return None
