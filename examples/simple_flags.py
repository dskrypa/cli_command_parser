#!/usr/bin/env python

from cli_command_parser import Command, Flag, main


class Example(Command):
    foo = Flag('-f')  # the default ``default`` value is False
    bar = Flag('--no-bar', '-B', default=True)

    def main(self):
        print(f'self.foo = {self.foo!r}')
        print(f'self.bar = {self.bar!r}')


if __name__ == '__main__':
    main()
