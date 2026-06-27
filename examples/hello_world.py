#!/usr/bin/env python
"""
Example ``Hello World`` implementation using CLI Command Parser.
"""

from cli_command_parser import Command, Option, main


class HelloWorld(Command, epilog='Contact <example@fake.org> with any issues'):
    """Simple greeting example"""

    name = Option('-n', default='World', help='The person to say hello to')
    count = Option('-c', type=int, default=1, help='Number of times to repeat the message')

    def main(self):
        for _ in range(self.count):
            print(f'Hello {self.name}!')


if __name__ == '__main__':
    main()
