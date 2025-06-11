#!/usr/bin/env python

import logging

from cli_command_parser import Command, SubCommand, Counter

log = logging.getLogger(__name__)


class Base(Command):
    sub_cmd = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def __init__(self):
        if self.verbose > 1:
            log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s'
        else:
            log_fmt = '%(message)s'

        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)


@Base.sub_cmd.register('run foo', help='Run foo')  # Aliases can have their own help text
class Foo(Base, help='Print foo'):
    # This is registered with both ``run foo`` and ``foo`` as names for this command - both can be used
    def main(self):
        print('foo')
        log.debug('[foo] this is a debug log')


class Bar(Base, choice='run bar', help='Print bar'):
    # This is registered with ``run bar`` as the name for this command instead of ``bar``
    def main(self):
        print('bar')
        log.debug('[bar] this is a debug log')


@Base.sub_cmd.register(help='Print baz')
class Baz(Command):
    # This is registered as a subcommand of Base, named ``baz``, but it does not share parameters with Base
    def main(self):
        print('baz')
        # The next line will never appear in output because Base.__init__ will not be called for this subcommand
        log.debug('[baz] this is a debug log')


if __name__ == '__main__':
    Base.parse_and_run()
