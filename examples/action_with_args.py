#!/usr/bin/env python

from cli_command_parser import Command, Action, Positional


class Example(Command):
    action = Action(help='The action to take')
    text = Positional(nargs='+', help='The text to print')

    @action(help='Echo the provided text')
    def echo(self):
        print(' '.join(self.text))

    @action(help='Split the provided text so that each word is on a new line')
    def split(self):
        print('\n'.join(self.text))


if __name__ == '__main__':
    Example.parse_and_run()
