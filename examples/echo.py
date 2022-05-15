#!/usr/bin/env python

from cli_command_parser import Command, Positional, main


class Echo(Command):
    text = Positional(nargs='*', help='The text to print')

    def main(self):
        print(' '.join(self.text))


if __name__ == '__main__':
    main()
