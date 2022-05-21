"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Optional, Any, Dict, FrozenSet

from .utils import Bool, _NotSet, cached_class_property

if TYPE_CHECKING:
    from .error_handling import ErrorHandler

__all__ = ['CommandConfig']


@dataclass
class CommandConfig:
    #: Whether multiple action_flag methods are allowed to run if they are all specified
    multiple_action_flags: Bool = True

    #: Whether action_flag methods are allowed to be combined with a positional Action method in a given CLI invocation
    action_after_action_flags: Bool = True

    #: Whether the --help / -h action_flag should be added
    add_help: Bool = True

    #: The :class:`~.error_handling.ErrorHandler` to be used by :meth:`~Command.__call__`
    error_handler: Optional['ErrorHandler'] = _NotSet

    #: Whether unknown arguments should be ignored (default: raise an exception when unknown arguments are encountered)
    ignore_unknown: Bool = False

    # #: Whether unknown options should be parsed (default: raise an exception when unknown arguments are encountered)
    # parse_unknown: Bool = False

    #: Whether missing required arguments should be allowed (default: raise an exception when they are missing)
    allow_missing: Bool = False

    #: Whether :meth:`Command._after_main_` should always be called, even if an exception was raised in
    #: :meth:`Command.main` (similar to a ``finally`` block)
    always_run_after_main: Bool = False

    # #: Whether handling of dashes (``-``) and underscores (``_``) in the middle of option names should be strict
    # #: (``True``) when processing user input, or if they should be allowed to be interchanged (``False``)
    # strict_option_punctuation: Bool = False
    #
    # #: Whether handling of spaces (`` ``), dashes (``-``), and underscores (``_``) in the middle of positional action
    # #: names should be strict (``True``) when processing user input, or if they should be allowed to be interchanged
    # #: (``False``)
    # strict_action_punctuation: Bool = False
    #
    # #: Whether handling of spaces (`` ``), dashes (``-``), and underscores (``_``) in the middle of positional sub
    # #: command names should be strict (``True``) when processing user input, or if they should be allowed to be
    # #: interchanged (``False``)
    # strict_sub_command_punctuation: Bool = False

    @cached_class_property
    def _field_names(cls) -> FrozenSet[str]:  # noqa
        return frozenset(field.name for field in fields(cls))

    def as_dict(self) -> Dict[str, Any]:
        """
        Return a dict representing the configured options.

        This was necessary because :func:`dataclasses.asdict` copies values, which breaks the use of _NotSet as a
        non-None sentinel value.
        """
        d = self.__dict__
        return {field: d[field] for field in self._field_names}  # noqa
