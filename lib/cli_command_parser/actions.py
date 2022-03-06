"""
Common actions.

:author: Doug Skrypa
"""

from .exceptions import ParserExit
from .parameters import action_flag


@action_flag('--help', '-h', order=float('-inf'), help='Show this help message and exit')
def help_action(self):
    cls = self.__class__
    print(cls.__class__.params(cls).formatter.format_help())
    raise ParserExit
