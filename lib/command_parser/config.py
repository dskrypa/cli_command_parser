"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from dataclasses import dataclass

from .utils import Bool

__all__ = ['CommandConfig']


@dataclass
class CommandConfig:
    #: Whether multiple action_flag methods are allowed to run if they are all specified
    multiple_action_flags: Bool = False

    #: Whether action_flag methods are allowed to be combined with a positional Action method in a given CLI invocation
    action_after_action_flags: Bool = False
