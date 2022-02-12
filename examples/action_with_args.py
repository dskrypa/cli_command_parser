#!/usr/bin/env python

from command_parser import Command, Action, Positional


class Example(Command):
    action = Action(help='The action to take')
    text = Positional(nargs='+')

    @action
    def echo(self):
        print(' '.join(self.text))

    @action
    def split(self):
        print('\n'.join(self.text))


if __name__ == '__main__':
    Example.parse_and_run()
