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
from .config import CommandConfig, AmbiguousComboMode
from .exceptions import CommandDefinitionError, ParameterDefinitionError, ParamsMissing
from .exceptions import AmbiguousShortForm, AmbiguousCombo
from .parameters.base import ParamBase, Parameter, BaseOption, BasePositional
from .parameters import SubCommand, PassThru, ActionFlag, ParamGroup, Action, Option

if TYPE_CHECKING:
    from .context import Context
    from .formatting.commands import CommandHelpFormatter
    from .typing import CommandCls

__all__ = ['CommandParameters']

OptionMap = Dict[str, BaseOption]
ActionFlags = List[ActionFlag]


class CommandParameters:
    command: CommandCls                                  #: The Command associated with this CommandParameters object
    formatter: CommandHelpFormatter                      #: The formatter used for this Command's help text
    command_parent: Optional[CommandCls] = None          #: The parent Command, if any
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
    _deferred_positionals: List[BasePositional] = ()     #: Positional Parameters that are deferred to sub commands
    option_map: OptionMap                                #: Mapping of {--opt / -opt: Parameter}

    def __init__(self, command: CommandCls, command_parent: Optional[CommandCls], config: CommandConfig):
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
    def all_positionals(self) -> List[BasePositional]:
        try:
            if not self.parent.sub_command:
                return self.parent.all_positionals + self.positionals
        except AttributeError:
            pass
        return self.positionals

    def get_positionals_to_parse(self, ctx: Context) -> List[BasePositional]:
        positionals = self.all_positionals
        if not positionals:
            return []
        for i, param in enumerate(positionals):
            if not ctx.num_provided(param):
                return [p for p in positionals[i:]]
        return []

    @cached_property
    def always_available_action_flags(self) -> Tuple[ActionFlag, ...]:
        """
        The :paramref:`.ActionFlag.before_main` :class:`.ActionFlag` actions that are always available, even if parsing
        failed (such as the one for ``--help``).
        """
        return tuple(af for af in self.action_flags if af.always_available)

    @cached_property
    def formatter(self) -> CommandHelpFormatter:
        from .formatting.commands import CommandHelpFormatter

        if self.config is None:
            formatter_factory = CommandHelpFormatter
        else:
            formatter_factory = self.config.command_formatter or CommandHelpFormatter
        formatter = formatter_factory(self.command, self)
        formatter.maybe_add_positionals(self.all_positionals)
        formatter.maybe_add_option(self._pass_thru)
        formatter.maybe_add_options(self.options)
        formatter.maybe_add_groups(self.groups)
        return formatter

    @cached_property
    def _classified_combo_options(self) -> Tuple[Dict[str, BaseOption], Dict[str, BaseOption]]:
        multi_char_combos = {}
        single_char_combos = {}
        for combo, param in self.combo_option_map.items():
            if len(combo) == 1:
                single_char_combos[combo] = param
            else:
                multi_char_combos[combo] = param
        return single_char_combos, multi_char_combos

    @cached_property
    def _potentially_ambiguous_combo_options(self) -> Dict[str, Tuple[BaseOption, Dict[str, BaseOption]]]:
        single_char_combos, multi_char_combos = self._classified_combo_options
        if not multi_char_combos:
            return {}

        ambiguous_combo_options = {}
        for combo, param in multi_char_combos.items():
            singles = {c: single_char_combos[c] for c in combo if c in single_char_combos}
            if singles:
                ambiguous_combo_options[combo] = (param, singles)

        return ambiguous_combo_options

    @property
    def _has_help(self) -> bool:
        return help_action in self.always_available_action_flags or (self.parent and self.parent._has_help)

    # region Initialization

    def _iter_parameters(self) -> Iterator[ParamBase]:
        name_param_map = {}  # Allow subclasses to override names, but not within a given command
        for attr, param in self.command.__dict__.items():
            if attr.startswith('__') or not isinstance(param, ParamBase):  # Name mangled Parameters are still processed
                continue
            try:
                other_attr, other_param = name_param_map[param.name]
            except KeyError:
                name_param_map[param.name] = (attr, param)
                yield param
            else:
                raise CommandDefinitionError(
                    'Name conflict - multiple parameters within a Command cannot have the same name - conflicting'
                    f' params: {other_attr}={other_param}, {attr}={param}'
                )

    def _process_parameters(self):
        """
        Process all of the :class:`.Parameter` / :class:`.ParamGroup` members in the associated :class:`.Command` class.
        """
        positionals = []
        options = []
        groups = set()

        for param in self._iter_parameters():
            if isinstance(param, BasePositional):
                positionals.append(param)
            elif isinstance(param, BaseOption):
                options.append(param)
            elif isinstance(param, ParamGroup):
                # Groups will only be discovered here when defined with `as` - ex: `with ParamGroup(...) as foo:`
                # Group members will always be discovered at the top level since context managers share the outer scope
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
                _find_groups(groups, param)

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
        unfollowable = action_or_sub_cmd = split_index = None
        parent = self.parent
        if parent and parent._deferred_positionals:
            params = parent._deferred_positionals + params

        for i, param in enumerate(params):
            if unfollowable:
                if 0 in unfollowable.nargs:
                    why = 'because it is a positional that is not required'
                else:
                    why = 'because it accepts a variable number of arguments with no specific choices defined'
                raise CommandDefinitionError(
                    f'Additional Positional parameters cannot follow {unfollowable} {why} - param={param!r} is invalid'
                )
            elif isinstance(param, (SubCommand, Action)):
                if action_or_sub_cmd:
                    raise CommandDefinitionError(
                        f'Only 1 Action xor SubCommand is allowed in a given Command - {self.command.__name__} cannot'
                        f' contain both {action_or_sub_cmd} and {param}'
                    )
                elif isinstance(param, SubCommand):
                    self.sub_command = action_or_sub_cmd = param
                    split_index = i + 1
                    if param.has_choices and 0 in param.nargs:  # It has local choices or is not required
                        unfollowable = param
                else:  # It's an Action
                    self.action = action_or_sub_cmd = param
                    if not param.has_choices:
                        raise CommandDefinitionError(f'No choices were registered for {self.action}')
            elif 0 in param.nargs or (param.nargs.variable and not param.has_choices):
                unfollowable = param

        if split_index:
            if self.sub_command.has_local_choices:
                self._deferred_positionals = params[split_index:]
            else:
                params, self._deferred_positionals = params[:split_index], params[split_index:]

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

        if self.config and self.config.ambiguous_short_combos == AmbiguousComboMode.STRICT:
            self._strict_ambiguous_short_combo_check()

    def _strict_ambiguous_short_combo_check(self):
        potentially_ambiguous_combo_options = self._potentially_ambiguous_combo_options
        if not potentially_ambiguous_combo_options:
            return

        param_conflicts_map = {
            param: singles.values() for param, singles in potentially_ambiguous_combo_options.values()
        }
        raise AmbiguousShortForm(param_conflicts_map)

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
            grouped_ordered_flags[param.before_main][param.order].append(param)  # noqa  # PyCharm infers the wrong type

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

        if len(option) > 2:  # 2 due to '-' prefix
            self._ensure_combo_is_unambiguous(option)

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
        param = combo_option_map[key]
        if param.would_accept(value, short_combo=True):
            return [(key, param, value)]
        else:
            return [(c, combo_option_map[c], None) for c in option[1:]]

    def _ensure_combo_is_unambiguous(self, option: str):
        # Called by short_option_to_param_value_pairs after ensuring the length is > 1
        acm = AmbiguousComboMode.PERMISSIVE if not self.config else self.config.ambiguous_short_combos
        if acm == AmbiguousComboMode.IGNORE:
            return

        to_check = option[1:]  # Strip leading '-'
        potentially_ambiguous_combo_options = self._potentially_ambiguous_combo_options
        if acm == AmbiguousComboMode.PERMISSIVE and to_check in potentially_ambiguous_combo_options:
            return  # Permissive mode allows exact matches of multi-char short forms

        ambiguous = set()
        for multi, (param, singles) in potentially_ambiguous_combo_options.items():
            if multi in to_check:
                ambiguous.add(param)
                ambiguous.update(p for c, p in singles.items() if c in to_check)

        if ambiguous:
            raise AmbiguousCombo(ambiguous, option)

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
            try:
                params = command.__class__.params(command)
            except AttributeError:  # The target was None (it's a subcommand's local choice)
                continue
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

    def validate_groups(self):
        exc = None
        for group in self.groups:
            try:
                group.validate()
            except ParamsMissing as e:  # Let ParamConflict propagate before ParamsMissing
                if exc is None:
                    exc = e

        if exc is not None:
            raise exc

    def try_env_params(self, ctx: Context) -> Iterator[Option]:
        """Yields Option parameters that have an environment variable configured, and did not have any CLI values."""
        for param in self.options:
            try:
                param.env_var  # noqa
            except AttributeError:
                pass
            else:
                if ctx.num_provided(param) == 0:
                    yield param

    def required_check_params(self) -> Iterator[Parameter]:
        ignore = SubCommand
        yield from (p for p in self.all_positionals if p.required and not p.group and not isinstance(p, ignore))
        yield from (p for p in self.options if p.required and not p.group)
        pass_thru = self._pass_thru
        if pass_thru and pass_thru.required and not pass_thru.group:
            yield pass_thru


def _find_groups(groups: Set[ParamGroup], param: ParamBase):
    group = param.group
    while group:
        groups.add(group)
        group = group.group
