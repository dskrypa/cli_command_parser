#!/usr/bin/env python

from cli_command_parser import Command, Action, Positional, main


class Example(Command):
    action = Action(help='The action to take')
    text = Positional(nargs='+', help='The text to print')

    # Registering an action can be as simple as adding it as a decorator - the method's name will be registered as
    # the choice for users to provide, and the docstring will be used as the help text.
    @action
    def echo(self):
        """Echo the provided text"""
        print(' '.join(self.text))

    # Keyword arguments can be provided to override the defaults - `help` here takes precedence over the docstring
    @action(help='Split the provided text so that each word is on a new line')
    def split(self):
        """Print the provided text on separate lines"""
        print('\n'.join(self.text))

    # This choice value will be used instead of the method name
    @action(choice='double', help='Print the provided text twice')
    def print_twice(self):
        text = ' '.join(self.text)
        print(text)
        print(text)

    # Calling the action directly is just a shortcut for .register - both can be used the same way
    @action.register(help='Reverse the provided text')
    def reverse(self):
        print(' '.join(reversed(self.text)))


if __name__ == '__main__':
    main()
