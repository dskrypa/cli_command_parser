#!/usr/bin/env python

from cli_command_parser import Command, Positional, PassThru, main


class Wrapper(Command):
    hosts = Positional(nargs='+', help='The hosts on which the given command should be run')
    command = PassThru(help='The command to run')

    def main(self):
        for host in self.hosts:
            print(f'Would run on {host}: {self.command}')


if __name__ == '__main__':
    main()
