"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from dataclasses import dataclass, fields
from enum import Flag, Enum
from typing import TYPE_CHECKING, Optional, Any, Union, Callable, Type, Dict, FrozenSet

from .utils import Bool, FlagEnumMixin, _NotSet, cached_class_property

if TYPE_CHECKING:
    from .command_parameters import CommandParameters
    from .core import CommandType
    from .error_handling import ErrorHandler
    from .formatting.commands import CommandHelpFormatter
    from .formatting.params import ParamHelpFormatter
    from .parameters import ParamOrGroup

__all__ = ['CommandConfig', 'ShowDefaults', 'OptionNameMode']


# region Config Option Enums


class ShowDefaults(Flag):
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
    def _missing_(cls, value: Union[str, int]) -> 'ShowDefaults':
        if isinstance(value, str):
            try:
                return cls._member_map_[value.upper().replace('-', '_')]  # noqa
            except KeyError:
                expected = ', '.join(cls._member_map_)
                raise ValueError(f'Invalid {cls.__name__} value={value!r} - expected one of {expected}') from None
        return super()._missing_(value)

    def __or__(self, other: 'ShowDefaults') -> 'ShowDefaults':
        if ShowDefaults.NEVER in (self, other):
            return ShowDefaults.NEVER
        return super().__or__(other)  # noqa


class OptionNameMode(FlagEnumMixin, Flag):
    """
    How the default long form that is added for Option/Flag/Counter/etc. Parameters should handle underscores/dashes.

    Given a Parameter defined as ``foo_bar = Option(...)``, the default long form handling based on this setting would
    be:

    :UNDERSCORE: ``--foo_bar``
    :DASH: ``--foo-bar``
    :BOTH: Both ``--foo-bar`` and ``--foo_bar`` will be accepted

    If a long form is provided explicitly for a given optional Parameter, then this setting will be ignored.
    """

    # fmt: off
    UNDERSCORE = 1
    DASH = 2
    BOTH = 3
    # fmt: on


# endregion


class EnumConfigOption:
    """
    Descriptor that simplifies config option validation using Enums and works around dataclass property idiosyncrasies.
    """

    def __init__(self, enum_cls: Type[Enum], default: Enum):
        self.enum_cls = enum_cls
        self.default = default

    def __set_name__(self, owner: Type['CommandConfig'], name: str):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):
        if isinstance(value, EnumConfigOption):  # Workaround for initial value setting
            instance.__dict__[self.name] = self.default
        else:
            instance.__dict__[self.name] = self.enum_cls(value)


@dataclass
class CommandConfig:
    # region Error Handling Options

    #: The :class:`.ErrorHandler` to be used by :meth:`.Command.__call__`
    error_handler: Optional['ErrorHandler'] = _NotSet

    #: Whether :meth:`.Command._after_main_` should always be called, even if an exception was raised in
    #: :meth:`.Command.main` (similar to a ``finally`` block)
    always_run_after_main: Bool = False

    # endregion

    # region ActionFlag Options

    #: Whether multiple action_flag methods are allowed to run if they are all specified
    multiple_action_flags: Bool = True

    #: Whether action_flag methods are allowed to be combined with a positional Action method in a given CLI invocation
    action_after_action_flags: Bool = True

    # endregion

    # region Parsing Options

    #: Whether unknown arguments should be ignored (default: raise an exception when unknown arguments are encountered)
    ignore_unknown: Bool = False

    #: Whether missing required arguments should be allowed (default: raise an exception when they are missing)
    allow_missing: Bool = False

    #: Whether backtracking is enabled for positionals following params with variable nargs
    allow_backtrack: Bool = True

    #: How the default long form that is added for Option/Flag/Counter/etc. Parameters should handle underscores/dashes
    option_name_mode: OptionNameMode = EnumConfigOption(OptionNameMode, OptionNameMode.UNDERSCORE)

    # endregion

    # region Usage & Help Text Options

    #: Whether the ``--help`` / ``-h`` action_flag should be added
    add_help: Bool = True

    #: Whether the metavar for Parameters that accept values should default to the name of the specified type
    #: (default: the name of the parameter)
    use_type_metavar: Bool = False

    #: Whether the default value for Parameters should be shown in help text, and related behavior
    show_defaults: ShowDefaults = EnumConfigOption(ShowDefaults, ShowDefaults.MISSING | ShowDefaults.NON_EMPTY)

    #: Whether there should be a visual indicator in help text for the parameters that are members of a given group
    show_group_tree: Bool = False

    #: Whether mutually exclusive / dependent groups should include that fact in their descriptions
    show_group_type: Bool = True

    #: A callable that accepts 2 arguments, a :class:`.Command` class (not object) and a :class:`.CommandParameters`
    #: object, and returns a :class:`.CommandHelpFormatter`
    command_formatter: Callable[['CommandType', 'CommandParameters'], 'CommandHelpFormatter'] = None

    #: A callable that accepts a :class:`.Parameter` or :class:`.ParamGroup` and returns a :class:`.ParamHelpFormatter`
    param_formatter: Callable[['ParamOrGroup'], 'ParamHelpFormatter'] = None

    #: Whether the program version, author email, and documentation URL should be included in the help text epilog, if
    #: they were successfully detected
    extended_epilog: Bool = True

    #: Whether the top level script's docstring should be included in generated documentation
    show_docstring: Bool = True

    # endregion

    # region Planned Options

    # #: Whether handling of spaces (`` ``), dashes (``-``), and underscores (``_``) in the middle of positional action
    # #: names should be strict (``True``) when processing user input, or if they should be allowed to be interchanged
    # #: (``False``)
    # strict_action_punctuation: Bool = False
    #
    # #: Whether handling of spaces (`` ``), dashes (``-``), and underscores (``_``) in the middle of positional sub
    # #: command names should be strict (``True``) when processing user input, or if they should be allowed to be
    # #: interchanged (``False``)
    # strict_sub_command_punctuation: Bool = False

    # endregion

    @cached_class_property
    def _field_names(cls) -> FrozenSet[str]:  # noqa
        """Cache the names of the config options for use in :meth:`.as_dict`"""
        names = {f.name for f in fields(cls)}
        return frozenset(names)

    def as_dict(self) -> Dict[str, Any]:
        """
        Return a dict representing the configured options.

        This was necessary because :func:`dataclasses.asdict` copies values, which breaks the use of _NotSet as a
        non-None sentinel value.
        """
        d = self.__dict__
        return {f: d[f] for f in self._field_names}  # noqa
