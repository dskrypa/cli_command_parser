#!/usr/bin/env python

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, PROJECT_ROOT.joinpath('lib').as_posix())

from command_parser import Command, Counter, SubCommand, Action


class Base(Command):
    sub_cmd = SubCommand()
    verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

    def main(self, *args, **kwargs):
        log_fmt = '%(asctime)s %(levelname)s %(name)s %(lineno)d %(message)s' if self.verbose else '%(message)s'
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format=log_fmt)
        super().main(*args, **kwargs)


class Show(Base, cmd='show'):
    action = Action(help='What to show')

    @action
    def attrs(self):
        for attr, value in sorted(vars(self).items()):
            print(f'self.{attr} = {value!r}')

    @action
    def hello(self):
        print('Hello world!')


if __name__ == '__main__':
    Base.parse_and_run()
