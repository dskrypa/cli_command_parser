"""
Simplified example of subcommands defined in a separate module from the one the base Command was defined in.

:author: Doug Skrypa
"""

import logging

from cli_command_parser import Option

from .base import Example

log = logging.getLogger(__name__)


class HelloWorld(Example, choice='hello'):
    name = Option('-n', default='World', help='The person to say hello to')

    def main(self):
        print(f'Hello {self.name}!')


class Logs(Example):
    def main(self):
        log.debug('This is a debug log')
        log.info('This is an info log')
        log.warning('This is a warning log')
