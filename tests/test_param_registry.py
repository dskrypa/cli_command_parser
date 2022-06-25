#!/usr/bin/env python

from abc import ABC
from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import CommandDefinitionError, NoSuchOption
from cli_command_parser.parameters import Action, SubCommand, Positional
from cli_command_parser.testing import RedirectStreams


class TestParamRegistry(TestCase):
    def test_multiple_actions_rejected(self):
        class Foo(Command):
            a = Action()
            b = Action()
            a(Mock(__name__='baz'))

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parse([])

    def test_multiple_sub_cmds_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    def test_action_with_sub_cmd_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = SubCommand()
            foo(Mock(__name__='baz'))

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parse([])

    def test_action_after_sub_cmd_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = Action()

        with self.assertRaisesRegex(CommandDefinitionError, 'may not follow the sub command SubCommand'):
            Foo.parse([])

    def test_positional_after_sub_cmd_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'may not follow the sub command'):

            class Foo(Command):
                sub = SubCommand()
                pos = Positional()

            class Bar(Foo, choice='bar'):
                pass

    def test_no_help(self):
        class Foo(Command, add_help=False, error_handler=None):
            pass

        with self.assertRaises(NoSuchOption):
            Foo.parse_and_run(['-h'])

    def test_sub_command_adds_help(self):
        class Foo(Command, ABC):
            pass

        class Bar(Foo):
            pass

        with RedirectStreams(), self.assertRaises(SystemExit):
            Bar.parse_and_run(['-h'])

    def test_multiple_non_required_positionals_rejected(self):
        for a, b in (('?', '?'), ('?', '*'), ('*', '?'), ('*', '*')):
            with self.subTest(a=a, b=b):

                class Foo(Command):
                    foo = Positional(nargs=a)
                    bar = Positional(nargs=b)

                with self.assertRaises(CommandDefinitionError):
                    CommandMeta.params(Foo)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
