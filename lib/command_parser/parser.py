"""
:author: Doug Skrypa
"""

import logging
from collections import deque, defaultdict
from typing import TYPE_CHECKING, Optional, Iterator, Iterable

from .exceptions import CommandDefinitionError, ParameterDefinitionError, UsageError, NoSuchOption, MissingArgument
from .parameters import ParameterGroup, Action
from .parameters import SubCommand, BaseOption, Parameter, PassThru, ActionFlag, BasePositional as _Positional
from .utils import Args, Bool, ProgramMetadata

if TYPE_CHECKING:
    from .commands import CommandType

__all__ = ['CommandParser']
log = logging.getLogger(__name__)


class CommandParser:
    command: 'CommandType'
    command_parent: Optional['CommandType']
    parent: Optional['CommandParser'] = None
    sub_command: Optional[SubCommand] = None
    action: Optional[Action] = None
    pass_thru: Optional[PassThru] = None
    groups: list[ParameterGroup]
    _options: list[BaseOption]
    positionals: list[_Positional]
    long_options: dict[str, BaseOption]
    short_options: dict[str, BaseOption]
    short_combinable: dict[str, BaseOption]
    action_flags: list[ActionFlag]

    def __init__(self, command: 'CommandType', command_parent: 'CommandType' = None):
        self.command = command
        self.command_parent = command_parent
        self.positionals = []  # Not copied from the parent because they must be consumed before the child can be picked
        self.pos_group = ParameterGroup(description='Positional arguments')
        self.opt_group = ParameterGroup(description='Optional arguments')
        if command_parent is not None:
            self.parent = parent = command_parent.parser()
            self.groups = parent.groups.copy()
            self._options = parent._options.copy()
            self.long_options = parent.long_options.copy()
            self.short_options = parent.short_options.copy()

            self.opt_group.maybe_add_all(self._options)
        else:
            parent = None
            self.groups = []
            self._options = []
            self.long_options = {}
            self.short_options = {}

        short_combinable = self._process_parameters(self.command, parent)
        # Sort flags by reverse key length, but forward alphabetical key for keys with the same length
        self.short_combinable = {k: v for k, v in sorted(short_combinable.items(), key=lambda kv: (-len(kv[0]), kv[0]))}
        self.action_flags = self._process_action_flags()
        self.groups = sorted(self.groups)

    # region Initialization / Parameter Processing

    def _process_parameters(self, command: 'CommandType', parent: Optional['CommandParser']):
        short_combinable = parent.short_combinable.copy() if parent is not None else {}
        var_nargs_pos_param = None
        for attr, param in command.__dict__.items():
            if attr.startswith(('__', '_BaseCommand__', '_Command__')):
                continue
            elif isinstance(param, _Positional):
                var_nargs_pos_param = self._add_positional(param, var_nargs_pos_param)
            elif isinstance(param, BaseOption):
                self._add_option(param, short_combinable, command)
            elif isinstance(param, ParameterGroup):
                self.groups.append(param)
            elif isinstance(param, PassThru):
                if self.has_pass_thru():
                    raise CommandDefinitionError(f'Invalid PassThru {param=} - it cannot follow another PassThru param')
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
        if not param.group:
            self.pos_group.add(param)

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
        self._options.append(param)
        if not param.group:
            self.opt_group.add(param)
        _update_options(self.long_options, 'long_opts', param, command)
        _update_options(self.short_options, 'short_opts', param, command)
        _update_options(short_combinable, 'short_combinable', param, command)

    def _process_action_flags(self):
        a_flags = (p for p in self._options if isinstance(p, ActionFlag) and p.enabled)
        action_flags = sorted(a_flags, key=lambda p: p.priority)

        a_flags_by_prio: dict[float, list[ActionFlag]] = defaultdict(list)
        for param in action_flags:
            if param.func is None:
                raise ParameterDefinitionError(f'No function was registered for {param=}')
            a_flags_by_prio[param.priority].append(param)

        invalid = {}
        for prio, params in a_flags_by_prio.items():
            if len(params) > 1:
                if (group := next((p.group for p in params if p.group), None)) and group.mutually_exclusive:
                    if not all(p.group == group for p in params):
                        invalid[prio] = params
                else:
                    invalid[prio] = params

        if invalid:
            raise CommandDefinitionError(
                f'ActionFlag parameters must either have different priority values or be in a mutually exclusive'
                f' ParameterGroup - invalid parameters: {invalid}'
            )

        return action_flags

    # endregion

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self._options)
        return f'<{self.__class__.__name__}[command={self.command.__name__}, {positionals=}, {options=}]>'

    def contains(self, args: Args, item: str, recursive: Bool = True) -> bool:
        if self._contains(args, item):
            return True
        elif recursive and (sub_command := self.sub_command) is not None:
            for command in sub_command.choice_command_map.values():
                if command.parser().contains(args, item, recursive):
                    return True
        return False

    def _contains(self, args: Args, item: str) -> bool:
        """
        :param args: The raw / partially parsed arguments for this parser
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

    def parse_args(self, args: Args, allow_unknown: Bool = False) -> Optional['CommandType']:
        # log.debug(f'{self!r}.parse_args({args=}, {allow_unknown=})')
        if (sub_cmd_param := self.sub_command) is not None and not sub_cmd_param.choice_command_map:
            raise CommandDefinitionError(f'{self.command}.{sub_cmd_param.name} = {sub_cmd_param} has no sub Commands')

        _Parser(self, args).parse_args()
        for group in self.groups:
            group.check_conflicts(args)

        if (sub_command := self.sub_command) is not None:
            try:
                return sub_command.result(args)
            except UsageError:
                if not args.find_all(ActionFlag):  # propagate if --help or similar was not found
                    raise
        elif args.remaining and not allow_unknown:
            raise NoSuchOption('unrecognized arguments: {}'.format(' '.join(args.remaining)))

        return None

    def format_usage(self, delim: str = ' ') -> str:
        meta: ProgramMetadata = self.command._BaseCommand__meta
        if usage := meta.usage:
            return usage
        parts = ['usage:', meta.prog]
        for param in self.positionals:  # type: _Positional
            parts.append(param.format_usage())
        for param in self._options:  # type: BaseOption
            parts.append('[{}]'.format(param.format_usage(True)))
        return delim.join(parts)

    def format_help(
        self, width: int = 30, add_default: Bool = True, group_type: Bool = True, extended_epilog: Bool = True
    ):
        meta: ProgramMetadata = self.command._BaseCommand__meta
        parts = [self.format_usage(), '']
        if description := meta.description:
            parts += [description, '']

        groups = [self.pos_group, self.opt_group] + self.groups
        for group in groups:
            if group.parameters:
                parts.append(group.format_help(width=width, add_default=add_default, group_type=group_type))

        if epilog := meta.format_epilog(extended_epilog):
            parts.append(epilog)

        return '\n'.join(parts)


def _format_group(name: str, params: Iterable[Parameter], width: int = 30, add_default: Bool = True) -> Iterator[str]:
    yield name
    for param in params:
        yield param.format_help(width=width, add_default=add_default)

    yield ''


class _Parser:
    """Stateful parser used for a single pass of argument parsing"""

    def __init__(self, cmd_parser: CommandParser, args: Args):
        self.cmd_parser = cmd_parser
        self.long_options = cmd_parser.long_options
        self.short_options = cmd_parser.short_options
        self.short_combinable = cmd_parser.short_combinable
        self.deferred = None
        self.args = args

    def parse_args(self):
        args = self.args
        arg_deque = self.handle_pass_thru()
        self.deferred = args.remaining = []
        pos_iter = iter(self.cmd_parser.positionals)
        while arg_deque:
            arg = arg_deque.popleft()
            if arg == '--' or arg.startswith('---'):
                raise NoSuchOption(f'invalid argument: {arg}')
            elif arg.startswith('--'):
                self.handle_long(arg, arg_deque)
            elif arg.startswith('-') and arg != '-':
                self.handle_short(arg, arg_deque)
            else:
                try:
                    param = next(pos_iter)  # type: _Positional
                except StopIteration:
                    self.deferred.append(arg)
                else:
                    found = param.take_action(args, arg)
                    self.consume_values(param, arg_deque, found=found)

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
        if not (param_val_combos := self.split_short(arg)):
            return
        elif len(param_val_combos) == 1:
            param, value = param_val_combos[0]
            if value is not None or (param.accepts_none and not param.accepts_values):
                param.take_action(self.args, value)
            elif not self.consume_values(param, arg_deque) and param.accepts_none:
                param.take_action(self.args, None)
        else:
            last = param_val_combos[-1][0]
            for param, _ in param_val_combos[:-1]:
                param.take_action(self.args, None)

            if last.accepts_none and not last.accepts_values:
                last.take_action(self.args, None)
            elif not self.consume_values(last, arg_deque) and last.accepts_none:
                last.take_action(self.args, None)

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
        elif param.would_accept(self.args, value):
            return [(param, value)]
        else:
            try:
                return [(short_combinable[c], None) for c in arg[1:]]
            except KeyError:
                self.deferred.append(arg)
                return []

    def consume_values(self, param: Parameter, arg_deque: deque[str], found: int = 0) -> int:
        result = self._consume_values(param, arg_deque, found)
        param.result(self.args)  # Trigger validation errors, if any
        return result

    def _consume_values(self, param: Parameter, arg_deque: deque[str], found: int = 0) -> int:
        nargs = param.nargs
        while True:
            try:
                value = arg_deque.popleft()
            except IndexError as e:
                if nargs.satisfied(found):
                    return found
                raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}') from e
            else:
                if value.startswith('--'):
                    if nargs.satisfied(found):
                        arg_deque.appendleft(value)
                        return found
                    raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                elif value.startswith('-') and value != '-':
                    if self.cmd_parser.contains(self.args, value):
                        if nargs.satisfied(found):
                            arg_deque.appendleft(value)
                            return found
                        raise MissingArgument(param, f'expected {nargs.min} values, but only found {found}')
                    elif not param.would_accept(self.args, value):
                        if nargs.satisfied(found):
                            arg_deque.appendleft(value)
                            return found
                        raise NoSuchOption(f'invalid argument: {value}')

                try:
                    found += param.take_action(self.args, value)
                except UsageError:
                    if nargs.satisfied(found):
                        arg_deque.appendleft(value)
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
                'long_opts': 'long option',
                'short_opts': 'short option',
                'short_combinable': 'combinable short option',
            }
            opt_type = opt_type_names[attr]
            raise ParameterDefinitionError(
                f'{opt_type}={opt!r} conflict for {command=} between params {existing} and {param}'
            )
