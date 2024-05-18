"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections import ChainMap
from enum import Enum
from string import whitespace
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, Sequence, Type, TypeVar, Union, overload

from .exceptions import CommandDefinitionError
from .utils import FixedFlag, MissingMixin, _NotSet, positive_int

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .error_handling import ErrorHandler
    from .formatting.commands import CommandHelpFormatter
    from .formatting.params import ParamHelpFormatter
    from .typing import Bool, CommandType, ParamOrGroup

__all__ = [
    'CommandConfig',
    'ShowDefaults',
    'OptionNameMode',
    'SubcommandAliasHelpMode',
    'AmbiguousComboMode',
    'AllowLeadingDash',
    'DEFAULT_CONFIG',
]

CV = TypeVar('CV')
DV = TypeVar('DV')
ConfigValue = Union[CV, DV]


# region Config Option Enums


class ShowDefaults(FixedFlag):
    """
    Options for showing ``(default: <default>)`` in ``--help`` text.  Options can be combined, but
    :attr:`ShowDefaults.NEVER` will override all other options.

    If ``TRUTHY`` / ``NON_EMPTY`` / ``ANY`` are combined, then the most permissive (rightmost / highest value)
    option will be used.

    The ``MISSING`` option must be combined with one of ``TRUTHY`` / ``NON_EMPTY`` / ``ANY`` - using ``MISSING`` alone
    is equivalent to ``ShowDefaults.MISSING | ShowDefaults.NEVER``, which will result in no default values being shown.
    """

    # fmt: off
    NEVER = 1       #: Never include the default value in help text
    MISSING = 2     #: Only include the default value if ``default:`` is not already present
    TRUTHY = 4      #: Only include the default value if it is treated as True in a boolean context
    NON_EMPTY = 8   #: Only include the default value if it is not ``None`` or an empty container
    ANY = 16        #: Any default value, regardless of truthiness, will be included
    # fmt: on

    @classmethod
    def _missing_(cls, value: Union[str, int]) -> ShowDefaults:
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper().replace('-', '_')]  # noqa
            except KeyError:
                expected = ', '.join(cls._member_map_)
                raise ValueError(f'Invalid {cls.__name__} {value=} - expected one of {expected}') from None
        return super()._missing_(value)

    def __or__(self, other: ShowDefaults) -> ShowDefaults:
        if ShowDefaults.NEVER in (self, other):
            return ShowDefaults.NEVER
        return super().__or__(other)  # noqa


class OptionNameMode(FixedFlag):
    """
    How the default long form that is added for Option/Flag/Counter/etc. Parameters should handle underscores/dashes.

    Given a Parameter defined as ``foo_bar = Option(...)``, the default long form handling based on this setting would
    be:

    :UNDERSCORE: ``--foo_bar`` - the attribute name is used verbatim.
    :DASH: ``--foo-bar`` - any underscores present in the attribute name will be replaced with dashes (this is
      the default behavior).
    :BOTH: Both ``--foo-bar`` and ``--foo_bar`` will be accepted, and both will be displayed in help text.
    :BOTH_UNDERSCORE: Both ``--foo-bar`` and ``--foo_bar`` will be accepted, but only ``--foo_bar`` with be displayed
      in help text.  This may be useful for compatibility purposes, and helps prevent help text from being too
      cluttered.
    :BOTH_DASH: Both ``--foo-bar`` and ``--foo_bar`` will be accepted, but only ``--foo-bar`` with be displayed
      in help text.  This may be useful for compatibility purposes, and helps prevent help text from being too
      cluttered.
    :NONE: No long form option string will be added.  At least one short form option string must be defined.  Note that
      it is NOT necessary to use ``name_mode=None`` to prevent the automatic creation of long form option strings in
      general.  If any long form option strings are explicitly provided for a given Parameter, then an automatic one
      will not be added, regardless of value for this configuration option.

    If a long form is provided explicitly for a given optional Parameter, then this setting will be ignored.

    The value may be specified to Commands as ``option_name_mode=<mode>`` or to Parameters as ``name_mode=<mode>``,
    where ``<mode>`` is one of:

        - ``'_'`` or ``'-'`` or ``'*'`` or ``'*_'`` or ``'*-'`` or ``'_*'`` or ``'-*'`` or ``None``
        - ``OptionNameMode.UNDERSCORE`` or ``OptionNameMode.DASH`` or ``OptionNameMode.BOTH``
          or ``OptionNameMode.BOTH_UNDERSCORE`` or ``OptionNameMode.BOTH_DASH`` or ``OptionNameMode.NONE``
        - ``'underscore'`` or ``'dash'`` or ``'both'`` or ``'both_underscore'`` or ``'both_dash'`` or ``'none'``
    """

    # fmt: off
    UNDERSCORE = 1
    DASH = 2
    BOTH = 3                # = 1|2
    #                         & 4  -> display options set
    BOTH_UNDERSCORE = 15    # & 8  -> show only underscore version
    BOTH_DASH = 23          # & 16 -> show only dash version
    NONE = 32
    # fmt: on

    @classmethod
    def _missing_(cls, value: Union[str, int, None]) -> OptionNameMode:
        try:
            return OPT_NAME_MODE_ALIASES[value]
        except KeyError:
            pass
        return cls.NONE if value is None else super()._missing_(value)


OPT_NAME_MODE_ALIASES = {
    '-': OptionNameMode.DASH,
    '_': OptionNameMode.UNDERSCORE,
    '*': OptionNameMode.BOTH,
    '-_': OptionNameMode.BOTH,
    '_-': OptionNameMode.BOTH,
    '*_': OptionNameMode.BOTH_UNDERSCORE,
    '_*': OptionNameMode.BOTH_UNDERSCORE,
    '*-': OptionNameMode.BOTH_DASH,
    '-*': OptionNameMode.BOTH_DASH,
}


class SubcommandAliasHelpMode(MissingMixin, Enum):
    """
    Options for how subcommand aliases (alternate :ref:`choices<subcommand_cls_params>` specified for a given Command
    class that is registered as a subcommand / subclass of another Command) should be displayed in help text.

    If a given Command is defined without the ``choices=`` class keyword argument, or if the provided collection
    contained only one value, then this setting is ignored.

    The output based on each supported option:

    :REPEAT: Each alias will be on a separate line in the ``Subcommands:`` section, and each alias will repeat the
      description (if defined for the target Command) as if it was a separate subcommand
    :COMBINE: All of the aliases will be combined on the same line in the ``Subcommands:`` section, with the values
      displayed in a way that is similar to the way that the ``choices=`` values for other Parameters are displayed.
    :ALIAS: Each alias will be on a separate line in the ``Subcommands:`` section, but only the first choice/value will
      have the description (if defined for the target Command).  Subsequent aliases' descriptions will be replaced by
      ``Alias of: <first choice/alias value>``.
    """

    # fmt: off
    REPEAT = 'repeat'       # Repeat the description as if it was a separate subcommand
    COMBINE = 'combine'     # Combine aliases onto a single line
    ALIAS = 'alias'         # Indicate the subcommand that it is an alias for; do not repeat the description
    # fmt: on


CmdAliasMode = Union[SubcommandAliasHelpMode, str]


class AmbiguousComboMode(MissingMixin, Enum):
    """
    Options for handling potentially ambiguous combinations of short forms of Option / Flag / etc. Parameters.

    The behavior based on each supported option:

    :IGNORE: Ignore potentially ambiguous combinations of short options entirely.  Best effort parsing will be
      performed.
    :PERMISSIVE: Allow multi-char short options that overlap with a single char one for exact matches, but reject any
      user input that combines multiple short options when the combination contains a sequence that could be
      interpreted as a multi-char short option.
    :STRICT: Reject multi-char short options that overlap with a single char one before parsing, regardless of user
      input.
    """

    # fmt: off
    IGNORE = 'ignore'           # Ignore potentially ambiguous combinations of short options entirely
    PERMISSIVE = 'permissive'   # Allow multi-char short options that overlap with a single char one for exact matches
    STRICT = 'strict'           # Reject multi-char short options that overlap with a single char one before parsing
    # fmt: on


class AllowLeadingDash(Enum):
    """
    How a given Parameter should handle values with a leading dash (``-``).  Only configurable at the Parameter level,
    not the Command level.

    The behavior based on each supported option:

    :NUMERIC: Allow numeric values like ``-5`` and ``-1.3``, but reject values like ``-d``.
    :ALWAYS: Always allow values with a leading dash.
    :NEVER: Never allow values with a leading dash.
    """

    # fmt: off
    NUMERIC = 'numeric'     # Allow a leading dash when the value is numeric
    ALWAYS = 'always'       # Always allow a leading dash
    NEVER = 'never'         # Never allow a leading dash
    # fmt: on

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper()]  # noqa
            except KeyError:
                pass
        elif value is True:
            return cls.ALWAYS
        elif value is False:
            return cls.NEVER
        return super()._missing_(value)  # noqa


# endregion


# region Config Item Descriptors / Decorators


class ConfigItem(Generic[CV, DV]):
    """
    A single configurable setting in the :class:`CommandConfig`.

    :param default: Default config value to use if no explicit value is provided
    :param type: A class or other callable that will be called to validate/normalize provided values
    """

    __slots__ = ('default', 'type', 'name')

    def __init__(self, default: DV, type: Callable[..., CV] = None):  # noqa
        self.default = default
        self.type = type

    def __set_name__(self, owner: Type[CommandConfig], name: str):
        self.name = name
        owner.FIELDS.add(name)

    @overload
    def __get__(self, instance: None, owner: Type[CommandConfig]) -> ConfigItem[CV, DV]: ...

    @overload
    def __get__(self, instance: CommandConfig, owner: Type[CommandConfig]) -> ConfigValue: ...

    def __get__(self, instance, owner):
        try:
            return instance._data.get(self.name, self.default)
        except AttributeError:  # instance is None
            return self

    def __set__(self, instance: CommandConfig, value: ConfigValue):
        if instance._read_only:
            raise AttributeError(f'Unable to set attribute {self.name}={value!r} because {instance} is read-only')
        elif self.type is not None:
            value = self.type(value)
        instance._data[self.name] = value

    def __delete__(self, instance: CommandConfig):
        if instance._read_only:
            raise AttributeError(f'Unable to delete attribute {self.name} because {instance} is read-only')
        try:
            del instance._data[self.name]
        except KeyError as e:
            raise AttributeError(f'No {self.name!r} config was stored for {instance}') from e

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.default!r}, type={self.type!r})>'


class DynamicConfigItem(ConfigItem):
    # A ConfigItem with a setter :paramref:`.ConfigItem.type` defined as a method in :class:`CommandConfig`.

    __slots__ = ('__doc__',)

    def __init__(self, default: DV, type: Callable[..., CV]):  # noqa
        super().__init__(default, type)
        self.__doc__ = type.__doc__

    def __set__(self, instance: CommandConfig, value: ConfigValue):
        if instance._read_only:
            raise AttributeError(f'Unable to set attribute {self.name}={value!r} because {instance} is read-only')
        instance._data[self.name] = self.type(instance, value)


def config_item(default: DV):
    return lambda func: DynamicConfigItem(default, func)


# endregion


class CommandConfig:
    """Configuration options for Commands."""

    # Note: PyCharm may incorrectly think ConfigItem attrs are read only: https://youtrack.jetbrains.com/issue/PY-29770

    __slots__ = ('_data', '_read_only')
    _data: ChainMap
    _read_only: bool
    FIELDS = set()

    # region Error Handling Options

    #: The :class:`.ErrorHandler` to be used by :meth:`.Command.__call__`
    error_handler: Optional[ErrorHandler] = ConfigItem(_NotSet)

    #: Whether :meth:`.Command._after_main_` should always be called, even if an exception was raised in
    #: :meth:`.Command.main` (similar to a ``finally`` block)
    always_run_after_main: Bool = ConfigItem(False, bool)

    # endregion

    # region Parameter Options

    #: Whether inferring Parameter types from type annotations should be enabled
    allow_annotation_type: Bool = ConfigItem(True, bool)

    # endregion

    # region ActionFlag Options

    #: Whether multiple action_flag methods are allowed to run if they are all specified
    multiple_action_flags: Bool = ConfigItem(True, bool)

    #: Whether action_flag methods are allowed to be combined with a positional Action method in a given CLI invocation
    action_after_action_flags: Bool = ConfigItem(True, bool)

    # endregion

    # region Parsing Options

    #: Whether unknown arguments should be ignored (default: raise an exception when unknown arguments are encountered)
    ignore_unknown: Bool = ConfigItem(False, bool)

    #: Whether missing required arguments should be allowed (default: raise an exception when they are missing)
    allow_missing: Bool = ConfigItem(False, bool)

    #: Whether backtracking is enabled for positionals following params with variable nargs
    allow_backtrack: Bool = ConfigItem(True, bool)

    #: How the default long form that is added for Option/Flag/Counter/etc. Parameters should handle underscores/dashes
    option_name_mode: OptionNameMode = ConfigItem(OptionNameMode.DASH, OptionNameMode)

    #: Whether ambiguous combinations of positional choices should result in an :class:`.AmbiguousParseTree` error
    reject_ambiguous_pos_combos: Bool = ConfigItem(False, bool)  # EXPERIMENTAL

    #: How potentially ambiguous combinations of short forms of Option/Flag/etc. Parameters should be handled
    ambiguous_short_combos: AmbiguousComboMode = ConfigItem(AmbiguousComboMode.PERMISSIVE, AmbiguousComboMode)

    # endregion

    # region Usage & Help Text Options

    #: Whether the ``--help`` / ``-h`` action_flag should be added
    add_help: Bool = ConfigItem(True, bool)

    #: Whether the metavar for Parameters that accept values should default to the name of the specified type
    #: (default: the name of the parameter)
    use_type_metavar: Bool = ConfigItem(False, bool)

    #: Whether the default value for Parameters should be shown in help text, and related behavior
    show_defaults: ShowDefaults = ConfigItem(ShowDefaults.MISSING | ShowDefaults.NON_EMPTY, ShowDefaults)

    #: Whether Parameters that support reading their values from env variables should include the var names in help text
    show_env_vars: Bool = ConfigItem(True, bool)

    @config_item(None)
    def cmd_alias_mode(self, value: CmdAliasMode) -> CmdAliasMode:
        """How subcommand aliases should be displayed in help text."""
        try:
            return SubcommandAliasHelpMode(value)
        except ValueError:
            return value

    #: Whether Parameter `choices` values and Action / Subcommand choices should be sorted
    sort_choices: Bool = ConfigItem(False, bool)

    #: Delimiter to use between choices in usage / help text
    choice_delim: str = ConfigItem('|', str)

    #: Whether there should be a visual indicator in help text for the parameters that are members of a given group
    show_group_tree: Bool = ConfigItem(False, bool)

    @config_item(('\u00a6 ', '\u2551 ', '\u2502 '))
    def group_tree_spacers(self, value: tuple[str, str, str] | Sequence[str]) -> tuple[str, str, str]:
        """
        The spacer characters to use at the beginning of each line when :attr:`.show_group_tree` is True.

        The default spacers:

        +--------------------+-----------+------------------------------+
        | Parameter Type     | Character | Character Name               |
        +====================+===========+==============================+
        | Mutually Exclusive | \u00a6         | BROKEN BAR                   |
        +--------------------+-----------+------------------------------+
        | Mutually dependent | \u2551         | BOX DRAWINGS DOUBLE VERTICAL |
        +--------------------+-----------+------------------------------+
        | Other              | \u2502         | BOX DRAWINGS LIGHT VERTICAL  |
        +--------------------+-----------+------------------------------+

        :param value: A 3-tuple (or other sequence with 3 items) of spacer strings to be used for
          (mutually exclusive, mutually dependent, other) group members, respectively.
        :return: The validated and normalized value (or the default value if this property is accessed without
          providing explicit values)
        """
        # Note: extra spaces in the docstring table are intentional - the escape sequences each collapse to one char
        if isinstance(value, Sequence) and len(value) == 3 and all(isinstance(v, str) for v in value):
            return tuple(f'{v} ' if v and v[-1] not in whitespace else v for v in value)  # noqa
        raise CommandDefinitionError(
            f'Invalid group_tree_spacers={value!r} - expected a 3-tuple of 2-character strings'
        )

    #: Whether mutually exclusive / dependent groups should include that fact in their descriptions
    show_group_type: Bool = ConfigItem(True, bool)

    #: A callable that accepts 2 arguments, a :class:`.Command` class (not object) and a :class:`.CommandParameters`
    #: object, and returns a :class:`.CommandHelpFormatter`
    command_formatter: Callable[[CommandType, CommandParameters], CommandHelpFormatter] = ConfigItem(None)

    #: A callable that accepts a :class:`.Parameter` or :class:`.ParamGroup` and returns a :class:`.ParamHelpFormatter`
    param_formatter: Callable[[ParamOrGroup], ParamHelpFormatter] = ConfigItem(None)

    #: Whether the program version, author email, and documentation URL should be included in the help text epilog, if
    #: they were successfully detected
    extended_epilog: Bool = ConfigItem(True, bool)

    #: Width (in characters) for the usage column in help text, after which the parameter descriptions begin.
    usage_column_width: int = ConfigItem(30, int)

    #: Whether the :attr:`.usage_column_width` should be enforced for parameters with usage text parts that exceed it.
    #: By default, that setting only defines where the parameter descriptions begin.
    strict_usage_column_width: bool = ConfigItem(False, bool)

    @config_item(False)
    def wrap_usage_str(self, value: Any) -> Union[int, bool]:
        """
        Wrap the basic usage line after the specified number of characters, or automatically based on terminal size
        if ``True`` is specified instead.
        """
        if value is True or value is False:
            return value
        return positive_int(value, 'a bool or a positive integer', min_val=1)

    # endregion

    # region Documentation Generation Options

    #: Whether the top level script's docstring should be included in generated documentation
    show_docstring: Bool = ConfigItem(True, bool)

    #: Whether inherited descriptions should be included in subcommand sections of generated documentation
    show_inherited_descriptions: Bool = ConfigItem(False, bool)

    #: Maximum subcommand depth to include in generated documentation (default: include all)
    sub_cmd_doc_depth: int = ConfigItem(None, positive_int)

    # endregion

    def __init__(self, parent: Optional[CommandConfig] = None, read_only: bool = False, **kwargs):
        self._data = parent._data.new_child() if parent else ChainMap()
        self._read_only = read_only
        if kwargs:
            try:
                for key, val in kwargs.items():
                    setattr(self, key, val)
            except AttributeError:
                bad = set(kwargs).difference(self.FIELDS)
                raise TypeError(f'Invalid configuration - unsupported options: {", ".join(sorted(bad))}') from None

    def __repr__(self) -> str:
        settings = ', '.join(f'{k}={v!r}' for k, v in self.as_dict(False).items())
        return f'<{self.__class__.__name__}[depth={len(self._data.maps)}]({settings})>'

    def as_dict(self, full: Bool = True) -> dict[str, Any]:
        """Return a dict representing the configured options."""
        if full:
            return {key: getattr(self, key) for key in self.FIELDS}
        return {key: val for key, val in self._data.items() if key in self.FIELDS}


DEFAULT_CONFIG: CommandConfig = CommandConfig(read_only=True)
