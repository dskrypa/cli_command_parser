"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any, Union, Callable, Type, TypeVar, overload, Generic, Sequence, Dict

from .utils import Bool, FixedFlag, _NotSet

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .core import CommandType
    from .error_handling import ErrorHandler
    from .formatting.commands import CommandHelpFormatter
    from .formatting.params import ParamHelpFormatter
    from .parameters import ParamOrGroup

__all__ = ['CommandConfig', 'ShowDefaults', 'OptionNameMode', 'DEFAULT_CONFIG']

_ConfigValue = TypeVar('_ConfigValue')
ConfigValue = Union[_ConfigValue, Any]


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

    NEVER = 1       #: Never include the default value in help text
    MISSING = 2     #: Only include the default value if ``default:`` is not already present
    TRUTHY = 4      #: Only include the default value if it is treated as True in a boolean context
    NON_EMPTY = 8   #: Only include the default value if it is not ``None`` or an empty container
    ANY = 16        #: Any default value, regardless of truthiness, will be included

    @classmethod
    def _missing_(cls, value: Union[str, int]) -> ShowDefaults:
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper().replace('-', '_')]  # noqa
            except KeyError:
                expected = ', '.join(cls._member_map_)
                raise ValueError(f'Invalid {cls.__name__} value={value!r} - expected one of {expected}') from None
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

    :UNDERSCORE: ``--foo_bar``
    :DASH: ``--foo-bar``
    :BOTH: Both ``--foo-bar`` and ``--foo_bar`` will be accepted
    :BOTH_UNDERSCORE: Both ``--foo-bar`` and ``--foo_bar`` will be accepted, but only ``--foo_bar`` with be displayed
      in help text
    :BOTH_DASH: Both ``--foo-bar`` and ``--foo_bar`` will be accepted, but only ``--foo-bar`` with be displayed
      in help text

    If a long form is provided explicitly for a given optional Parameter, then this setting will be ignored.

    The value may be specified to Commands as ``option_name_mode=<mode>`` or to Parameters as ``name_mode=<mode>``,
    where ``<mode>`` is one of:

        - ``OptionNameMode.UNDERSCORE`` or ``OptionNameMode.DASH`` or ``OptionNameMode.BOTH``
          or ``OptionNameMode.BOTH_UNDERSCORE`` or ``OptionNameMode.BOTH_DASH``
        - ``'underscore'`` or ``'dash'`` or ``'both'`` or ``'both_underscore'`` or ``'both_dash'``
        - ``'_'`` or ``'-'`` or ``'*'`` or ``'*_'`` or ``'*-'``
    """

    UNDERSCORE = 1
    DASH = 2
    BOTH = 3                # = 1|2
    #                         & 4  -> display options set
    BOTH_UNDERSCORE = 15    # & 8  -> show only underscore version
    BOTH_DASH = 23          # & 16 -> show only dash version

    @classmethod
    def _missing_(cls, value: Union[str, int]) -> OptionNameMode:
        try:
            return OPT_NAME_MODE_ALIASES[value]
        except KeyError:
            pass
        return super()._missing_(value)


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


# endregion


class ConfigItem(Generic[_ConfigValue]):
    __slots__ = ('default', 'type', 'name')

    def __init__(self, default: ConfigValue, type: Callable[[Any], _ConfigValue] = None):  # noqa
        self.default = default
        self.type = type

    def __set_name__(self, owner: Type[CommandConfig], name: str):
        self.name = name
        owner.FIELDS.add(name)

    def get_value(self, instance: CommandConfig) -> ConfigValue:
        try:
            return instance.__dict__[self.name]
        except KeyError:
            pass

        for parent in instance.parents:
            try:
                return self.get_value(parent)
            except KeyError:
                pass

        raise KeyError

    @overload
    def __get__(self, instance: None, owner: Type[CommandConfig]) -> ConfigItem[_ConfigValue]:
        ...

    @overload
    def __get__(self, instance: CommandConfig, owner: Type[CommandConfig]) -> ConfigValue:
        ...

    def __get__(
        self, instance: Optional[CommandConfig], owner: Type[CommandConfig]
    ) -> Union[ConfigItem[_ConfigValue], ConfigValue]:
        if instance is None:
            return self

        try:
            return self.get_value(instance)
        except KeyError:
            return self.default

    def __set__(self, instance: CommandConfig, value: ConfigValue):
        if instance._read_only:
            raise AttributeError(f'Unable to set attribute {self.name}={value!r} because {instance} is read-only')
        elif self.type is not None:
            value = self.type(value)
        instance.__dict__[self.name] = value

    def __delete__(self, instance: CommandConfig):
        if instance._read_only:
            raise AttributeError(f'Unable to delete attribute {self.name} because {instance} is read-only')
        try:
            del instance.__dict__[self.name]
        except KeyError as e:
            raise AttributeError(f'No {self.name!r} config was stored for {instance}') from e

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.default!r}, type={self.type!r})>'


class CommandConfig:
    """Configuration options for Commands."""

    FIELDS = set()

    # region Error Handling Options

    #: The :class:`.ErrorHandler` to be used by :meth:`.Command.__call__`
    error_handler: Optional[ErrorHandler] = ConfigItem(_NotSet)

    #: Whether :meth:`.Command._after_main_` should always be called, even if an exception was raised in
    #: :meth:`.Command.main` (similar to a ``finally`` block)
    always_run_after_main: Bool = ConfigItem(False, bool)

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
    option_name_mode: OptionNameMode = ConfigItem(OptionNameMode.UNDERSCORE, OptionNameMode)

    # endregion

    # region Usage & Help Text Options

    #: Whether the ``--help`` / ``-h`` action_flag should be added
    add_help: Bool = ConfigItem(True, bool)

    #: Whether the metavar for Parameters that accept values should default to the name of the specified type
    #: (default: the name of the parameter)
    use_type_metavar: Bool = ConfigItem(False, bool)

    #: Whether the default value for Parameters should be shown in help text, and related behavior
    show_defaults: ShowDefaults = ConfigItem(ShowDefaults.MISSING | ShowDefaults.NON_EMPTY, ShowDefaults)

    #: Whether there should be a visual indicator in help text for the parameters that are members of a given group
    show_group_tree: Bool = ConfigItem(False, bool)

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

    #: Whether the top level script's docstring should be included in generated documentation
    show_docstring: Bool = ConfigItem(True, bool)

    #: Delimiter to use between choices in usage / help text
    choice_delim: str = ConfigItem('|', str)

    #: Width (in characters) for the usage column in help text
    usage_column_width: int = ConfigItem(30, int)

    #: Min width (in chars) for the usage column in help text after adjusting for group indentation / terminal width
    min_usage_column_width: int = ConfigItem(20, int)

    # endregion

    def __init__(self, parents: Optional[Sequence[CommandConfig]] = None, read_only: bool = False, **kwargs):
        self.parents = parents or ()
        self._read_only = read_only
        bad = {}
        for key, val in kwargs.items():
            if key in self.FIELDS:
                setattr(self, key, val)
            else:
                bad[key] = val
        if bad:
            raise ValueError(f'Invalid configuration - unsupported options: {", ".join(sorted(bad))}')

    def __repr__(self) -> str:
        settings = ', '.join(f'{k}={v!r}' for k, v in self.as_dict(False).items())
        cfg_str = f', {settings}' if settings else ''
        return f'<{self.__class__.__name__}(parents={self.parents!r}{cfg_str})>'

    def as_dict(self, full: Bool = True) -> Dict[str, Any]:
        """Return a dict representing the configured options."""
        if full:
            return {key: getattr(self, key) for key in self.FIELDS}
        return {key: val for key, val in self.__dict__.items() if key in self.FIELDS}


DEFAULT_CONFIG = CommandConfig(read_only=True)
