#!/usr/bin/env python

import logging

from cli_command_parser import Command, Counter, SubCommand, Action, get_formatter

log = logging.getLogger(__name__)


class Base(Command):
    sub_cmd = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def __init__(self):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose > 1 else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)


class Show(Base, choice='show', help='Show the results of an action'):
    action = Action(help='What to show')

    @action
    def attrs(self):
        for attr, value in sorted(vars(self).items()):
            print(f'self.{attr} = {value!r}')

    @action
    def hello(self):
        print('Hello world!')

    @action
    def log_test(self):
        log.debug('This is a debug log')
        log.info('This is an info log')
        log.warning('This is a warning log')

    @action
    def rst(self):
        print(get_formatter(Base).format_rst())


if __name__ == '__main__':
    Base.parse_and_run()
