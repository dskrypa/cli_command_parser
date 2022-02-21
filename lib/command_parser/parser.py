"""
:author: Doug Skrypa
"""

import logging
from collections import deque, defaultdict
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
from .parameters import (
    SubCommand,
    BaseOption,
    ParamBase,
    Parameter,
    PassThru,
    ActionFlag,
    ParamGroup,
    Action,
    BasePositional,
)
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
    groups: list[ParamGroup]
    options: list[BaseOption]
    positionals: list[BasePositional]
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

        short_combinable = self._process_parameters(parent)
        # Sort flags by reverse key length, but forward alphabetical key for keys with the same length
        self.short_combinable = {k: v for k, v in sorted(short_combinable.items(), key=lambda kv: (-len(kv[0]), kv[0]))}
        self.action_flags = self._process_action_flags()
        self.groups = sorted(self.groups)

    # region Initialization / Parameter Processing

    def _process_parameters(self, parent: Optional['CommandParser']) -> dict[str, BaseOption]:
        """
        Register all of the parameters defined in this parser's Command and handle any conflicts between them.

        :param parent: The parent command's CommandParser, if this parser's command has a parent.
        :return: Unsorted short combinable options
        """
        # This isn't stored as self.short_combinable yet because it needs to be sorted after initial processing
        short_combinable = parent.short_combinable.copy() if parent is not None else {}
        var_nargs_pos_param = None
        name_param_map = {}  # Allow sub-classes to override names, but not within a given command

        for attr, param in self.command.__dict__.items():
            if attr.startswith('__') or not isinstance(param, ParamBase):
                continue

            name = param.name
            try:
                other_attr, other_param = name_param_map[name]
            except KeyError:
                name_param_map[name] = (attr, param)
            else:
                raise CommandDefinitionError(
                    'Name conflict - multiple parameters within a Command cannot have the same name - conflicting'
                    f' params: {other_attr}={other_param}, {attr}={param}'
                )

            if isinstance(param, BasePositional):
                var_nargs_pos_param = self._add_positional(param, var_nargs_pos_param)
            elif isinstance(param, BaseOption):
                self._add_option(param, short_combinable)
            elif isinstance(param, ParamGroup):
                self.formatter.maybe_add(param)
                self.groups.append(param)
            elif isinstance(param, PassThru):
                if self.has_pass_thru():
                    raise CommandDefinitionError(f'Invalid PassThru {param=} - it cannot follow another PassThru param')
                self.formatter.maybe_add(param)
                self.pass_thru = param
            else:
                raise CommandDefinitionError(
                    f'Unexpected type={param.__class__} for {param=} - custom parameters must extend'
                    ' BasePositional, BaseOption, or ParamGroup'
                )

        return short_combinable

    def _add_positional(
        self, param: BasePositional, var_nargs_param: Optional[BasePositional]
    ) -> Optional[BasePositional]:
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

    def _add_option(self, param: BaseOption, short_combinable: dict[str, BaseOption]):
        command = self.command
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
                f' or be in a mutually exclusive ParamGroup - invalid parameters: {invalid}'
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
                _split_short(item, args, self.short_options, self.short_combinable)
            except NotAShortOption:
                return False
            else:
                return True
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

    def parse_args(
        self,
        args: 'Args',
        allow_unknown: Bool = False,
        allow_missing: Bool = False,
    ) -> Optional['CommandType']:
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
        elif (
            (missing := self._get_missing(args))
            and not allow_missing
            and (not self.action or self.action not in missing)  # excluded because it provides a better error message
        ):
            if help_action not in args:
                raise ParamsMissing(missing)
        elif args.remaining and not allow_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(args.remaining)))

        return None

    def arg_dict(self, args: 'Args', exclude: Collection['Parameter'] = ()) -> dict[str, Any]:
        if (parent := self.parent) is not None:
            arg_dict = parent.arg_dict(args, exclude)
        else:
            arg_dict = {}

        for group in (self.positionals, self.options, (self.pass_thru,)):
            for param in group:
                if param and param not in exclude:
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
        self.arg_deque = None
        self.args = args
        self.positionals = self.cmd_parser.positionals.copy()

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
                except NotAShortOption:
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
        if (pass_thru := self.cmd_parser.pass_thru) is not None:
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
        try:
            param = self.positionals.pop(0)  # type: BasePositional
        except IndexError:
            self.deferred.append(arg)
        else:
            found = param.take_action(self.args, arg)
            self.consume_values(param, found=found)

    def handle_long(self, arg: str):
        try:
            param, value = self.split_long(arg)
        except KeyError:
            self.deferred.append(arg)
        else:
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(self.args, value)
            elif not self.consume_values(param) and param.accepts_none:
                param.take_action(self.args, None)

    def handle_short(self, arg: str):
        param_val_combos = _split_short(arg, self.args, self.short_options, self.short_combinable)
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

    def split_long(self, arg: str) -> tuple[BaseOption, Optional[str]]:
        try:
            return self.long_options[arg], None
        except KeyError:
            if '=' in arg:
                key, value = arg.split('=', 1)
                return self.long_options[key], value
            else:
                raise

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
                    if self.cmd_parser.contains(self.args, value):
                        # log.debug(f'{value=} will not be used with {param=} - it is also a parameter')
                        return self._finalize_consume(param, value, found)
                    elif not param.would_accept(self.args, value):
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


def _split_short(
    option: str, args: 'Args', short_options: dict[str, BaseOption], short_combinable: dict[str, BaseOption]
) -> list[tuple[BaseOption, Optional[str]]]:
    try:
        option, value = option.split('=', 1)
    except ValueError:
        value = None
    try:
        return [(short_options[option], value)]
    except KeyError:
        if value is not None:
            raise NotAShortOption from None

    key, value = option[1], option[2:]
    # value will never be empty if key is a valid option because by this point, option is not a short option
    if (param := short_combinable.get(key)) is None:
        raise NotAShortOption
    elif param.would_accept(args, value, short_combo=True):
        return [(param, value)]
    else:
        try:
            return [(short_combinable[c], None) for c in option[1:]]
        except KeyError as e:
            raise NotAShortOption from e


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
