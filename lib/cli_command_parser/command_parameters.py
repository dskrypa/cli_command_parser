"""
The CommandParameters class in this module is used to process all of the attributes of a given :class:`.Command` when
it is defined to collect its :class:`.Parameter` / :class:`.ParamGroup` members.  It also checks for conflicts between
parameter definitions.

It has some involvement in the parsing process for :class:`.BaseOption` parameters.

:author: Doug Skrypa
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Optional, Collection, List, Dict, Set, Tuple

try:
    from functools import cached_property
except ImportError:
    from .compat import cached_property

from .context import ctx
from .exceptions import CommandDefinitionError, ParameterDefinitionError
from .formatting.commands import CommandHelpFormatter
from .parameters import (
    Parameter,
    SubCommand,
    BaseOption,
    ParamBase,
    PassThru,
    ActionFlag,
    ParamGroup,
    Action,
    BasePositional,
)

if TYPE_CHECKING:
    from .config import CommandConfig
    from .core import CommandType

__all__ = ['CommandParameters']
log = logging.getLogger(__name__)


class CommandParameters:
    command: 'CommandType'
    formatter: CommandHelpFormatter
    command_parent: Optional['CommandType'] = None
    parent: Optional['CommandParameters'] = None
    action: Optional[Action] = None
    _pass_thru: Optional[PassThru] = None
    sub_command: Optional[SubCommand] = None
    action_flags: List[ActionFlag]
    options: List[BaseOption]
    combo_option_map: Dict[str, BaseOption]
    groups: List[ParamGroup]
    positionals: List[BasePositional]
    option_map: Dict[str, BaseOption]

    def __init__(self, command: 'CommandType', command_parent: 'CommandType' = None):
        self.command = command
        if command_parent:
            self.command_parent = command_parent
            self.parent = command_parent.__class__.params(command_parent)

        config: 'CommandConfig' = command.__class__.config(command)
        if config is None:
            formatter_factory = CommandHelpFormatter
        else:
            formatter_factory = config.command_formatter or CommandHelpFormatter

        self.formatter = formatter_factory(command, self)
        self._process_parameters()

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self.options)
        return (
            f'<{self.__class__.__name__}[command={self.command.__name__},'
            f' positionals={positionals!r}, options={options!r}]>'
        )

    @property
    def pass_thru(self) -> Optional[PassThru]:
        if self._pass_thru:
            return self._pass_thru
        elif self.parent:
            return self.parent.pass_thru
        return None

    @cached_property
    def always_available_action_flags(self) -> Tuple[ActionFlag, ...]:
        """
        The :paramref:`.ActionFlag.before_main` :class:`.ActionFlag` actions that are always available, even if parsing
        failed (such as the one for ``--help``).
        """
        return tuple(af for af in self.action_flags if af.always_available)

    # region Initialization

    def _process_parameters(self):
        """
        Process all of the :class:`.Parameter` / :class:`.ParamGroup` members in the associated :class:`.Command` class.
        """
        name_param_map = {}  # Allow subclasses to override names, but not within a given command
        positionals = []
        options = []
        groups = set()

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
                positionals.append(param)
            elif isinstance(param, BaseOption):
                options.append(param)
            elif isinstance(param, ParamGroup):
                groups.add(param)
            elif isinstance(param, PassThru):
                if self.pass_thru:
                    raise CommandDefinitionError(
                        f'Invalid PassThru param={param!r} - it cannot follow another PassThru param'
                    )
                self._pass_thru = param
                self.formatter.maybe_add_param(param)
            else:
                raise CommandDefinitionError(
                    f'Unexpected type={param.__class__} for param={param!r} - custom parameters must extend'
                    ' BasePositional, BaseOption, or ParamGroup'
                )

            if param.group:
                groups.update(_get_groups(param))

        self._process_positionals(positionals)
        self._process_options(options)
        self._process_groups(groups)

    def _process_groups(self, groups: Set[ParamGroup]):
        if self.parent:
            _groups, groups = groups, self.parent.groups.copy()
            groups.extend(_groups)

        self.formatter.maybe_add_group(*groups)
        self.groups = sorted(groups)

    def _process_positionals(self, params: List[BasePositional]):
        var_nargs_param = None
        for param in params:
            if self.sub_command is not None:
                raise CommandDefinitionError(
                    f'Positional param={param!r} may not follow the sub command {self.sub_command} - re-order the'
                    ' positionals, move it into the sub command(s), or convert it to an optional parameter'
                )
            elif var_nargs_param is not None:
                raise CommandDefinitionError(
                    f'Additional Positional parameters cannot follow {var_nargs_param} because it accepts'
                    f' a variable number of arguments with no specific choices defined - param={param!r} is invalid'
                )

            if isinstance(param, (SubCommand, Action)) and param.command is self.command:
                if self.action:  # self.sub_command being already defined is handled above
                    raise CommandDefinitionError(
                        f'Only 1 Action xor SubCommand is allowed in a given Command - {self.command.__name__} cannot'
                        f' contain both {self.action} and {param}'
                    )
                elif isinstance(param, SubCommand):
                    self.sub_command = param
                else:
                    self.action = param

            if param.nargs.variable and not param.choices:
                var_nargs_param = param

        self.positionals = params
        self.formatter.maybe_add_param(*params)

    def _process_options(self, params: Collection[BaseOption]):
        parent = self.parent
        if parent:
            option_map = parent.option_map.copy()
            combo_option_map = parent.combo_option_map.copy()
            options = parent.options.copy()
        else:
            option_map = {}
            combo_option_map = {}
            options = []

        for param in params:
            options.append(param)
            for opt_type, opt_strs in (('long option', param.long_opts), ('short option', param.short_opts)):
                for opt in opt_strs:
                    try:
                        existing = option_map[opt]
                    except KeyError:
                        option_map[opt] = param
                        if opt_type == 'short option':
                            combo_option_map[opt[1:]] = param
                    else:
                        raise CommandDefinitionError(
                            f'{opt_type}={opt!r} conflict for command={self.command!r} between {existing} and {param}'
                        )

        self.formatter.maybe_add_param(*options)
        self.options = options
        self.option_map = option_map
        self._process_action_flags(options)
        self.combo_option_map = {k: v for k, v in sorted(combo_option_map.items(), key=lambda kv: (-len(kv[0]), kv[0]))}

    def _process_action_flags(self, options: List[BaseOption]):
        action_flags = sorted((p for p in options if isinstance(p, ActionFlag)))
        grouped_ordered_flags = {True: defaultdict(list), False: defaultdict(list)}
        for param in action_flags:
            if param.func is None:
                raise ParameterDefinitionError(f'No function was registered for param={param!r}')
            grouped_ordered_flags[param.before_main][param.order].append(param)

        invalid = {}
        for before_main, prio_params in grouped_ordered_flags.items():  # noqa  # pycharm forgets dict has .items...
            for prio, params in prio_params.items():  # noqa
                if len(params) > 1:
                    group = next((p.group for p in params if p.group), None)
                    if group and group.mutually_exclusive:
                        if not all(p.group == group for p in params):
                            invalid[(before_main, prio)] = params
                    else:
                        invalid[(before_main, prio)] = params

        if invalid:
            raise CommandDefinitionError(
                f'ActionFlag parameters with the same before/after main setting must either have different order values'
                f' or be in a mutually exclusive ParamGroup - invalid parameters: {invalid}'
            )

        self.action_flags = action_flags

    # endregion

    # region Option Processing

    def get_option_param_value_pairs(self, option: str) -> Optional[Tuple[BaseOption, ...]]:
        if option.startswith('---'):
            return None
        elif option.startswith('--'):
            try:
                param, value = self.long_option_to_param_value_pair(option)
            except KeyError:
                return None
            else:
                return (param,)  # noqa
        elif option.startswith('-'):
            try:
                param_value_pairs = self.short_option_to_param_value_pairs(option)
            except KeyError:
                return None
            else:
                return tuple(param for param, value in param_value_pairs)
        else:
            return None

    def long_option_to_param_value_pair(self, option: str) -> Tuple[BaseOption, Optional[str]]:
        try:
            return self.option_map[option], None
        except KeyError:
            if '=' in option:
                option, value = option.split('=', 1)
                return self.option_map[option], value
            else:
                raise

    def short_option_to_param_value_pairs(self, option: str) -> List[Tuple[BaseOption, Optional[str]]]:
        try:
            option, value = option.split('=', 1)
        except ValueError:
            value = None

        try:
            param = self.option_map[option]
        except KeyError:
            if value is not None:
                raise
        else:
            return [(param, value)]

        key, value = option[1], option[2:]
        # value will never be empty if key is a valid option because by this point, option is not a short option
        param = self.combo_option_map[key]
        if param.would_accept(value, short_combo=True):
            return [(param, value)]
        else:
            combo_option_map = self.combo_option_map
            return [(combo_option_map[c], None) for c in option[1:]]

    def find_option_that_accepts_values(self, option: str) -> Optional[BaseOption]:
        if option.startswith('--'):
            param, value = self.long_option_to_param_value_pair(option)
            if param.accepts_values:
                return param
        elif option.startswith('-'):
            for param, value in self.short_option_to_param_value_pairs(option):
                if param.accepts_values:
                    return param
        else:
            raise ValueError(f'Invalid option={option!r}')
        return None

    def find_nested_option_that_accepts_values(self, option: str) -> Optional[BaseOption]:
        if not self.sub_command:
            return None

        for choice in self.sub_command.choices.values():
            command = choice.target
            params = command.__class__.params(command)
            try:
                param = params.find_option_that_accepts_values(option)
            except KeyError:
                pass
            else:
                if param is not None:
                    return param

            param = params.find_nested_option_that_accepts_values(option)
            if param is not None:
                return param

        return None

    def find_nested_pass_thru(self) -> Optional[PassThru]:
        if not self.sub_command:
            return None

        for choice in self.sub_command.choices.values():
            command = choice.target
            params = command.__class__.params(command)
            if params._pass_thru:
                return params._pass_thru

        return None

    # endregion

    def missing(self) -> List['Parameter']:
        ignore = SubCommand
        missing: List['Parameter'] = [
            p for p in self.positionals if p.required and ctx.num_provided(p) == 0 and not isinstance(p, ignore)
        ]
        missing.extend(p for p in self.options if p.required and ctx.num_provided(p) == 0)
        return missing


def _get_groups(param: ParamBase) -> Set[ParamGroup]:
    groups = set()
    group = param.group
    if group:
        groups.add(group)
        groups.update(_get_groups(group))
    return groups
