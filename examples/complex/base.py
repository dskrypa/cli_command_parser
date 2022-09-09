"""
The base Command for a simplified example of a complex set of Commands defined across multiple modules.

:author: Doug Skrypa
"""

import logging

from cli_command_parser import Command, Counter, SubCommand


class Example(Command, prog='complex_example.py', option_name_mode='-', show_group_tree=True):
    sub_cmd = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def _init_command_(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)
