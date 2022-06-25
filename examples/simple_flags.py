#!/usr/bin/env python

from cli_command_parser import Command, Flag, TriFlag, main


class Example(Command):
    foo = Flag('-f')  # the default ``default`` value is False
    bar = Flag('--no-bar', '-B', default=True)
    spam = TriFlag(
        '-s', alt_short='-S', name_mode='-', help='Whether spam should be enabled (default: depends on other factors)'
    )

    def main(self):
        print(f'self.foo = {self.foo!r}')
        print(f'self.bar = {self.bar!r}')
        print(f'self.spam = {self.spam!r}')


if __name__ == '__main__':
    main()
