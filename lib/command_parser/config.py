"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Optional, Any

from .utils import Bool, _NotSet

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

    #: The :class:`~.error_handling.ErrorHandler` to be used by :meth:`~Command.run`
    error_handler: Optional['ErrorHandler'] = _NotSet

    #: Whether unknown arguments should be allowed (default: raise an exception when unknown arguments are encountered)
    allow_unknown: Bool = False

    #: Whether missing required arguments should be allowed (default: raise an exception when they are missing)
    allow_missing: Bool = False

    def as_dict(self) -> dict[str, Any]:
        """
        Return a dict representing the configured options.

        This was necessary because :func:`dataclasses.asdict` copies values, which breaks the use of _NotSet as a
        non-None sentinel value.
        """
        return {name: getattr(self, name) for field in fields(self) if (name := field.name)}
