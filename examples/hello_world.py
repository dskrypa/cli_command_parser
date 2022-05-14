#!/usr/bin/env python

from cli_command_parser import Command, Option, main


class HelloWorld(Command, description='Simple greeting example'):
    name = Option('-n', default='World', help='The person to say hello to')

    def main(self):
        print(f'Hello {self.name}!')


if __name__ == '__main__':
    main()
