"""
Configuration options for Command behavior.

:author: Doug Skrypa
"""

from dataclasses import dataclass

from .utils import Bool

__all__ = ['CommandConfig']


@dataclass
class CommandConfig:
    multiple_action_flags: Bool = False
    action_after_action_flags: Bool = False
