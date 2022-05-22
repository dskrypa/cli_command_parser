"""
Common actions.

:author: Doug Skrypa
"""

from .exceptions import ParserExit
from .parameters import action_flag


@action_flag('--help', '-h', order=float('-inf'), always_available=True, help='Show this help message and exit')
def help_action(self):
    """The ``--help`` / ``-h`` action.  Prints help text, then exits."""
    cls = self.__class__
    print(cls.__class__.params(cls).formatter.format_help())
    raise ParserExit
