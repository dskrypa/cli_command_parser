"""
The CommandParameters class in this module is used to process all of the attributes of a given :class:`.Command` when
it is defined to collect its :class:`.Parameter` / :class:`.ParamGroup` members.  It also checks for conflicts between
parameter definitions.

It has some involvement in the parsing process for :class:`.BaseOption` parameters.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Optional, Collection, Iterator, List, Dict, Set, Tuple

try:
    from functools import cached_property
except ImportError:
    from .compat import cached_property

from .actions import help_action
from .exceptions import CommandDefinitionError, ParameterDefinitionError
from .formatting.commands import CommandHelpFormatter
from .parameters.base import ParamBase, Parameter, BaseOption, BasePositional
from .parameters import SubCommand, PassThru, ActionFlag, ParamGroup, Action

if TYPE_CHECKING:
    from .config import CommandConfig
    from .core import CommandType

__all__ = ['CommandParameters']

OptionMap = Dict[str, BaseOption]
ActionFlags = List[ActionFlag]


class CommandParameters:
    command: CommandType                                 #: The Command associated with this CommandParameters object
    formatter: CommandHelpFormatter                      #: The formatter used for this Command's help text
    command_parent: Optional[CommandType] = None         #: The parent Command, if any
    parent: Optional[CommandParameters] = None           #: The parent Command's CommandParameters
    action: Optional[Action] = None                      #: An Action Parameter, if specified
    _pass_thru: Optional[PassThru] = None                #: A PassThru Parameter, if specified
    sub_command: Optional[SubCommand] = None             #: A SubCommand Parameter, if specified
    action_flags: ActionFlags                            #: List of action flags
    split_action_flags: Tuple[ActionFlags, ActionFlags]  #: Action flags split by before/after main
    options: List[BaseOption]                            #: List of optional Parameters
    combo_option_map: OptionMap                          #: Mapping of {short opt: Parameter} (no dash characters)
    groups: List[ParamGroup]                             #: List of ParamGroup objects
    positionals: List[BasePositional]                    #: List of positional Parameters
    option_map: OptionMap                                #: Mapping of {--opt / -opt: Parameter}

    def __init__(self, command: CommandType, command_parent: Optional[CommandType], config: CommandConfig):
        self.command = command
        if command_parent is not None:
            self.command_parent = command_parent
            self.parent = command_parent.__class__.params(command_parent)

        self.config = config
        self._process_parameters()

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self.options)
        cls_name = self.__class__.__name__
        return f'<{cls_name}[command={self.command.__name__}, positionals={positionals!r}, options={options!r}]>'

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

    @cached_property
    def formatter(self) -> CommandHelpFormatter:
        if self.config is None:
            formatter_factory = CommandHelpFormatter
        else:
            formatter_factory = self.config.command_formatter or CommandHelpFormatter
        formatter = formatter_factory(self.command, self)
        formatter.maybe_add_option(self._pass_thru)
        formatter.maybe_add_positionals(self.positionals)
        formatter.maybe_add_options(self.options)
        formatter.maybe_add_groups(self.groups)
        return formatter

    @property
    def _has_help(self) -> bool:
        return help_action in self.always_available_action_flags or (self.parent and self.parent._has_help)

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
            if attr.startswith('__') or not isinstance(param, ParamBase):  # Name mangled Parameters are still processed
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
            else:
                raise CommandDefinitionError(
                    f'Unexpected type={param.__class__} for param={param!r} - custom parameters must extend'
                    ' BasePositional, BaseOption, or ParamGroup'
                )

            if param.group:
                groups.update(_get_groups(param))

        if self.config and self.config.add_help and (not self.parent or not self.parent._has_help):
            options.append(help_action)

        self._process_positionals(positionals)
        self._process_options(options)
        self._process_groups(groups)

    def _process_groups(self, groups: Set[ParamGroup]):
        if self.parent:
            _groups, groups = groups, self.parent.groups.copy()
            groups.extend(_groups)

        self.groups = sorted(groups)

    def _process_positionals(self, params: List[BasePositional]):
        var_nargs_param = None
        for param in params:
            if self.sub_command:
                raise CommandDefinitionError(
                    f'Positional param={param!r} may not follow the sub command {self.sub_command} - re-order the'
                    ' positionals, move it into the sub command(s), or convert it to an optional parameter'
                )
            elif var_nargs_param:
                raise CommandDefinitionError(
                    f'Additional Positional parameters cannot follow {var_nargs_param} because it accepts'
                    f' a variable number of arguments with no specific choices defined - param={param!r} is invalid'
                )

            # if isinstance(param, (SubCommand, Action)) and param.command is self.command:
            if isinstance(param, (SubCommand, Action)):
                if self.action:  # self.sub_command being already defined is handled above
                    raise CommandDefinitionError(
                        f'Only 1 Action xor SubCommand is allowed in a given Command - {self.command.__name__} cannot'
                        f' contain both {self.action} and {param}'
                    )
                elif isinstance(param, SubCommand):
                    self.sub_command = param
                else:
                    self.action = param
                    if not param.choices:
                        raise CommandDefinitionError(f'No choices were registered for {self.action}')

            if param.nargs.variable and not param.choices:
                var_nargs_param = param

        self.positionals = params

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
            opts = param.option_strs
            self._process_option_strs(param, 'long', opts.long, option_map, combo_option_map)
            self._process_option_strs(param, 'short', opts.short, option_map, combo_option_map)

        self.options = options
        self.option_map = option_map
        self._process_action_flags(options)
        self.combo_option_map = dict(sorted(combo_option_map.items(), key=lambda kv: (-len(kv[0]), kv[0])))  # noqa

    def _process_option_strs(
        self, param: BaseOption, opt_type: str, opt_strs: List[str], option_map: OptionMap, combo_option_map: OptionMap
    ):
        for opt in opt_strs:
            try:
                existing = option_map[opt]
            except KeyError:
                option_map[opt] = param
                if opt_type == 'short':
                    combo_option_map[opt[1:]] = param
            else:
                raise CommandDefinitionError(
                    f'{opt_type} option={opt!r} conflict for command={self.command!r} between {existing} and {param}'
                )

    def _process_action_flags(self, options: List[BaseOption]):
        action_flags = sorted((p for p in options if isinstance(p, ActionFlag)))
        grouped_ordered_flags = {True: defaultdict(list), False: defaultdict(list)}
        for param in action_flags:
            if param.func is None:
                raise ParameterDefinitionError(f'No function was registered for param={param!r}')
            grouped_ordered_flags[param.before_main][param.order].append(param)

        found_non_always = False
        invalid = {}
        for before_main, prio_params in grouped_ordered_flags.items():
            for prio, params in prio_params.items():
                param: ActionFlag = params[0]  # Don't pop and check `if params` - all are needed for the group check
                if found_non_always and param.always_available:
                    invalid[(before_main, prio)] = param
                elif not param.always_available:
                    found_non_always = True

                if len(params) > 1:
                    group = next((p.group for p in params if p.group), None)
                    if group and group.mutually_exclusive:
                        if any(p.group != group for p in params):
                            invalid[(before_main, prio)] = params
                    else:
                        invalid[(before_main, prio)] = params

        if invalid:
            raise CommandDefinitionError(
                f'ActionFlag parameters with the same before/after main setting must either have different order values'
                f' or be in a mutually exclusive ParamGroup, and always_available ActionFlags must all be ordered'
                f' before any that are not always available - invalid parameters: {invalid}'
            )

        n_before = len(grouped_ordered_flags[True])
        self.action_flags = action_flags
        self.split_action_flags = action_flags[:n_before], action_flags[n_before:]

    # endregion

    # region Option Processing

    def get_option_param_value_pairs(self, option: str) -> Optional[Tuple[BaseOption, ...]]:
        if option.startswith('---'):
            return None
        elif option.startswith('--'):
            try:
                opt, param, value = self.long_option_to_param_value_pair(option)
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
                return tuple(param for opt, param, value in param_value_pairs)
        else:
            return None

    def long_option_to_param_value_pair(self, option: str) -> Tuple[str, BaseOption, Optional[str]]:
        try:
            return option, self.option_map[option], None
        except KeyError:
            if '=' in option:
                option, value = option.split('=', 1)
                return option, self.option_map[option], value
            else:
                raise

    def short_option_to_param_value_pairs(self, option: str) -> List[Tuple[str, BaseOption, Optional[str]]]:
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
            return [(option, param, value)]

        key, value = option[1], option[2:]
        # value will never be empty if key is a valid option because by this point, option is not a short option
        combo_option_map = self.combo_option_map
        # TODO: #7 - detect ambiguous combined options if configured to reject them
        param = combo_option_map[key]
        if param.would_accept(value, short_combo=True):
            return [(key, param, value)]
        else:
            return [(c, combo_option_map[c], None) for c in option[1:]]

    def find_option_that_accepts_values(self, option: str) -> Optional[BaseOption]:
        if option.startswith('--'):
            param = self.long_option_to_param_value_pair(option)[1]
            if param.accepts_values:
                return param
        elif option.startswith('-'):
            for _, param, _ in self.short_option_to_param_value_pairs(option):
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

    def required_check_params(self) -> Iterator[Parameter]:
        ignore = SubCommand
        yield from (p for p in self.positionals if not isinstance(p, ignore))
        yield from self.options
        if self._pass_thru:
            yield self._pass_thru


def _get_groups(param: ParamBase) -> Set[ParamGroup]:
    groups = set()
    group = param.group
    if group:
        groups.add(group)
        groups.update(_get_groups(group))
    return groups
