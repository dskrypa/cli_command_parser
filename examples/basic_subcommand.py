#!/usr/bin/env python

from cli_command_parser import Command, SubCommand, main


class Base(Command):
    sub_cmd = SubCommand()


class Foo(Base, help='Print foo'):
    def main(self):
        print('foo')


class Bar(Base, help='Print bar'):
    def main(self):
        print('bar')


if __name__ == '__main__':
    main()
