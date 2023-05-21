"""
The CommandParameters class in this module is used to process all of the attributes of a given :class:`.Command` when
it is defined to collect its :class:`.Parameter` / :class:`.ParamGroup` members.  It also checks for conflicts between
parameter definitions.

It has some involvement in the parsing process for :class:`.BaseOption` parameters.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Iterator, List, Dict, Set, Tuple

from .actions import help_action
from .config import CommandConfig, AmbiguousComboMode
from .exceptions import CommandDefinitionError, ParameterDefinitionError, ParamsMissing
from .exceptions import AmbiguousShortForm, AmbiguousCombo
from .parameters.base import ParamBase, Parameter, BaseOption, BasePositional
from .parameters import SubCommand, PassThru, ActionFlag, ParamGroup, Action, Option

if TYPE_CHECKING:
    from .context import Context
    from .formatting.commands import CommandHelpFormatter
    from .typing import CommandCls, Strings

__all__ = ['CommandParameters']

OptionMap = Dict[str, BaseOption]
ActionFlags = List[ActionFlag]


class CommandParameters:
    command: CommandCls                                  #: The Command associated with this CommandParameters object
    formatter: CommandHelpFormatter                      #: The formatter used for this Command's help text
    command_parent: Optional[CommandCls]                 #: The parent Command, if any
    parent: Optional[CommandParameters]                  #: The parent Command's CommandParameters
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

    def __init__(
        self,
        command: CommandCls,
        command_parent: Optional[CommandCls],
        parent_params: Optional[CommandParameters],
        config: CommandConfig,
    ):
        self.command = command
        self.command_parent = command_parent
        self.parent = parent_params
        self.config = config
        self._process_parameters()

    def __repr__(self) -> str:
        positionals = len(self.positionals)
        options = len(self.options)
        cls_name = self.__class__.__name__
        return f'<{cls_name}[command={self.command.__name__}, {positionals=}, {options=}]>'

    @property
    def pass_thru(self) -> Optional[PassThru]:
        if pass_thru := self._pass_thru:
            return pass_thru
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
        if positionals := self.all_positionals:
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

        formatter_factory = self.config.command_formatter or CommandHelpFormatter
        formatter = formatter_factory(self.command, self)
        formatter.maybe_add_positionals(self.all_positionals)
        formatter.maybe_add_option(self._pass_thru)
        formatter.maybe_add_options(self.options)
        formatter.maybe_add_groups(self.groups)
        return formatter

    @property
    def _has_help(self) -> bool:
        return help_action in self.always_available_action_flags or (self.parent and self.parent._has_help)

    # region Initialization

    def _iter_parameters(self) -> Iterator[ParamBase]:
        name_param_map = {}  # Allow subclasses to override names, but not within a given command
        for item in self.command.__dict__.items():
            attr, param = item
            if attr.startswith('__') or not isinstance(param, ParamBase):  # Name mangled Parameters are still processed
                continue
            elif (other := name_param_map.setdefault(param.name, item)) is item:
                yield param  # There was no other param with the same name
            else:
                other_attr, other_param = other
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
                    raise CommandDefinitionError(f'Invalid PassThru {param=} - it cannot follow another PassThru param')
                self._pass_thru = param
            else:
                raise CommandDefinitionError(
                    f'Unexpected type={param.__class__} for {param=} - custom parameters must extend'
                    ' BasePositional, BaseOption, or ParamGroup'
                )

            param_group = param
            while param_group := param_group.group:
                groups.add(param_group)

        if self.config.add_help and self.command_parent is not None and (not self.parent or not self.parent._has_help):
            options.append(help_action)

        self._process_positionals(positionals)
        self._process_options(options)
        self._process_groups(groups)

    def _process_groups(self, groups: Set[ParamGroup]):
        if parent := self.parent:
            self.groups = sorted((*parent.groups, *groups)) if groups else parent.groups.copy()
        else:
            self.groups = sorted(groups) if groups else []

    def _process_positionals(self, params: List[BasePositional]):
        unfollowable = action_or_sub_cmd = split_index = None
        if (parent := self.parent) and (deferred := parent._deferred_positionals):
            params = deferred + params

        for i, param in enumerate(params):
            if unfollowable:
                if 0 in unfollowable.nargs:
                    why = 'because it is a positional that is not required'
                else:
                    why = 'because it accepts a variable number of arguments with no specific choices defined'
                raise CommandDefinitionError(
                    f'Additional Positional parameters cannot follow {unfollowable} {why} - {param=} is invalid'
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

    def _process_options(self, params: List[BaseOption]):
        if parent := self.parent:
            option_map = parent.option_map.copy()
            combo_option_map = parent.combo_option_map.copy()
            self.options = parent.options + params
        else:
            option_map = {}
            combo_option_map = {}
            self.options = params

        for param in params:
            opts = param.option_strs
            if not opts.has_min_opts():  # This is checked here and not earlier due to possible additions in set_name
                raise ParameterDefinitionError(f'No option strings were registered for {param=}')

            long_opts, short_opts = opts.get_sets()
            self._process_option_strs(param, 'long', long_opts, option_map)
            if short_opts:
                self._process_option_strs(param, 'short', short_opts, option_map)
                for opt in short_opts:
                    combo_option_map[opt[1:]] = param

        self.option_map = option_map
        self._process_action_flags()
        self.combo_option_map = dict(sorted(combo_option_map.items(), key=_sort_kv))
        if self.config.ambiguous_short_combos == AmbiguousComboMode.STRICT:
            self._strict_ambiguous_short_combo_check()

    def _process_option_strs(self, param: BaseOption, opt_type: str, opt_strs: Strings, option_map: OptionMap):
        for option in opt_strs:
            if option not in option_map:
                option_map[option] = param
            else:
                # It is more efficient for the typical code path to avoid a try/except or .get call since the
                # likelihood of a conflict is extremely low, and the extra lookup is acceptable for the error case.
                existing = option_map[option]
                raise CommandDefinitionError(
                    f'{opt_type} {option=} conflict for command={self.command!r} between {existing} and {param}'
                )

    def _process_action_flags(self):
        action_flags = sorted(p for p in self.options if isinstance(p, ActionFlag))
        grouped_ordered_flags = {True: defaultdict(list), False: defaultdict(list)}
        for param in action_flags:
            if param.func is None:
                raise ParameterDefinitionError(f'No function was registered for {param=}')
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
                    group = next((g for p in params if (g := p.group)), None)
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

    # region Ambiguous Short Combo Handling

    def _strict_ambiguous_short_combo_check(self):
        # Called during initial Option processing when using AmbiguousComboMode.STRICT
        if not (potentially_ambiguous_combo_options := self._potentially_ambiguous_combo_options):
            return

        param_conflicts_map = {
            param: singles.values() for param, singles in potentially_ambiguous_combo_options.values()
        }
        raise AmbiguousShortForm(param_conflicts_map)

    @cached_property
    def _classified_combo_options(self) -> Tuple[OptionMap, OptionMap]:
        multi_char_combos = {}
        items = self.combo_option_map.items()
        for combo, param in items:
            if len(combo) == 1:  # combo_option_map is sorted in reverse length order, so all following will be 1 char
                single_char_combos = {combo: param}
                single_char_combos.update(items)
                return single_char_combos, multi_char_combos
            multi_char_combos[combo] = param
        return {}, multi_char_combos

    @cached_property
    def _potentially_ambiguous_combo_options(self) -> Dict[str, Tuple[BaseOption, OptionMap]]:
        single_char_combos, multi_char_combos = self._classified_combo_options
        if not multi_char_combos:
            return {}
        return _find_ambiguous_combos(single_char_combos, multi_char_combos)

    @cached_property
    def _nested_potentially_ambiguous_combo_options(self):
        single_char_combos, multi_char_combos = self._classified_combo_options
        single_char_combos = single_char_combos.copy()
        multi_char_combos = multi_char_combos.copy()
        for params in self._iter_nested_params():
            nested_single_char_combos, nested_multi_char_combos = params._classified_combo_options
            single_char_combos.update(nested_single_char_combos)
            multi_char_combos.update(nested_multi_char_combos)

        if not multi_char_combos:
            return {}
        return _find_ambiguous_combos(single_char_combos, multi_char_combos)

    def _is_combo_potentially_ambiguous(self, option: str) -> Optional[bool]:
        # Called by short_option_to_param_value_pairs after ensuring the length is > 1
        to_check = option[1:]  # Strip leading '-'
        # Note: len(to_check) will never be 2 here - this is only called if len(option) > 2
        potentially_ambiguous_combo_options = self._nested_potentially_ambiguous_combo_options
        acm = self.config.ambiguous_short_combos
        if acm == AmbiguousComboMode.PERMISSIVE and to_check in potentially_ambiguous_combo_options:
            return True  # Permissive mode allows exact matches of multi-char short forms
        elif acm == AmbiguousComboMode.IGNORE:
            return None

        ambiguous = set()
        for multi, (param, singles) in potentially_ambiguous_combo_options.items():
            if multi in to_check:
                ambiguous.add(param)
                ambiguous.update(p for c, p in singles.items() if c in to_check)

        if ambiguous:
            raise AmbiguousCombo(ambiguous, option)

        return False

    # endregion

    # region Option Processing

    def _iter_nested_params(self) -> Iterator[CommandParameters]:
        if sub_command := self.sub_command:
            get_params = self.command.__class__.params
            for choice in sub_command.choices.values():
                if (command := choice.target) is not None:  # None indicates it's a subcommand's local choice
                    yield get_params(command)

    def long_option_to_param_value_pair(self, option: str) -> Tuple[str, BaseOption, Optional[str]]:
        option, eq, value = option.partition('=')
        return option, self.option_map[option], (value if eq else None)

    def has_matching_short_option(self, option: str) -> bool:
        try:
            self.short_option_to_param_value_pairs(option)
        except KeyError:
            return False
        return True

    def short_option_to_param_value_pairs(self, option: str) -> List[Tuple[str, BaseOption, Optional[str]]]:
        option, eq, value = option.partition('=')
        if eq:  # An `=` was present in the string
            # Note: if the option is not in this Command's option_map, the KeyError is handled by CommandParser
            return [(option, self.option_map[option], value)]
        else:
            value = None

        try:
            param = self.option_map[option]
        except KeyError:
            opt_len = len(option)
            if opt_len < 2 or (opt_len > 2 and self._is_combo_potentially_ambiguous(option)):
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
            # Multi-char short options can never be combined with each other, but single-char ones can
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
            raise ValueError(f'Invalid {option=}')
        return None

    def find_nested_option_that_accepts_values(self, option: str) -> Optional[BaseOption]:
        for params in self._iter_nested_params():
            try:
                param = params.find_option_that_accepts_values(option)
            except KeyError:
                pass
            else:
                if param is not None:
                    return param

            if (param := params.find_nested_option_that_accepts_values(option)) is not None:
                return param

        return None

    def find_nested_pass_thru(self) -> Optional[PassThru]:
        for params in self._iter_nested_params():
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
            if param.env_var and ctx.num_provided(param) == 0:
                yield param

    def required_check_params(self) -> Iterator[Parameter]:
        ignore = SubCommand
        yield from (p for p in self.all_positionals if p.required and not p.group and not isinstance(p, ignore))
        yield from (p for p in self.options if p.required and not p.group)
        if (pass_thru := self._pass_thru) and pass_thru.required and not pass_thru.group:
            yield pass_thru


def _find_ambiguous_combos(
    single_char_combos: OptionMap, multi_char_combos: OptionMap
) -> Dict[str, Tuple[BaseOption, OptionMap]]:
    ambiguous_combo_options = {}
    for combo, param in multi_char_combos.items():
        if singles := {c: single_char_combos[c] for c in combo if c in single_char_combos}:
            ambiguous_combo_options[combo] = (param, singles)

    return ambiguous_combo_options


def _sort_kv(kv):
    k = kv[0]
    return -len(k), k
