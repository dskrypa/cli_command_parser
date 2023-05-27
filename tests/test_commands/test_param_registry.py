#!/usr/bin/env python

from abc import ABC
from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command
from cli_command_parser.core import CommandMeta, get_params
from cli_command_parser.exceptions import CommandDefinitionError, NoSuchOption
from cli_command_parser.parameters import Action, SubCommand, Positional, Counter, Flag, Option
from cli_command_parser.parameters.actions import Store
from cli_command_parser.parameters.base import Parameter
from cli_command_parser.testing import RedirectStreams, ParserTest


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

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
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

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parse([])

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

                with self.assertRaisesRegex(CommandDefinitionError, 'it is a positional that is not required'):
                    CommandMeta.params(Foo)


class CommandParamsTest(TestCase):
    def test_reprs(self):
        class Foo(Command):
            bar = Positional()

        rep = repr(get_params(Foo))
        self.assertIn('Foo', rep)
        self.assertIn('positionals=', rep)
        self.assertIn('options=', rep)

    def test_params_parent(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Baz(Foo):
            pass

        self.assertIs(get_params(Baz).parent, get_params(Foo))

    def test_params_find_option_rejects_non_option(self):
        class Foo(Command):
            pass

        with self.assertRaises(ValueError):
            get_params(Foo).find_option_that_accepts_values('bar')

    def test_bad_custom_param_rejected(self):
        class Test(Store):
            pass

        class TestParam(Parameter, actions=(Test,)):
            pass

        class Foo(Command):
            bar = TestParam('test')

        with self.assertRaisesRegex(CommandDefinitionError, 'custom parameters must extend'):
            Foo.parse([])

    def test_redefined_param_rejected(self):
        class Foo(Command):
            cmd = SubCommand()
            bar = Flag('-b')

        class Bar(Foo):
            bar = Counter('-b')

        with self.assertRaisesRegex(CommandDefinitionError, 'conflict for command=.* between'):
            Foo.parse(['bar'])


class ParamNameConflictHandlingTest(ParserTest):
    def test_explicit_name_conflict_before(self):
        class Foo(Command):
            bar = Option(name='baz')
            baz = Option()

        with self.assertRaisesRegex(CommandDefinitionError, 'Name conflict.*bar=Option.*baz=Option'):
            Foo.parse([])

    def test_explicit_name_conflict_after(self):
        class Foo(Command):
            baz = Option()
            bar = Option(name='baz')

        with self.assertRaisesRegex(CommandDefinitionError, 'Name conflict.*baz=Option.*bar=Option'):
            Foo.parse([])

    def test_sub_cmd_param_override_rejected(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            bar = Option()

        class Baz(Foo):
            bar = Option()

        self.assert_parse_fails(Baz, [], CommandDefinitionError, 'conflict for command=.* between')
        self.assert_parse_fails(Foo, ['baz'], CommandDefinitionError, 'conflict for command=.* between')

    def test_sub_cmd_param_name_override_ok(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            bar = Option()

        class Baz(Foo):
            baz = Option(name='bar')

        success_cases = [
            (['baz', '--bar', 'a', '--baz', 'b'], {'sub_cmd': 'baz', 'bar': 'b'}),
            (['baz', '--bar', 'a'], {'sub_cmd': 'baz', 'bar': None}),
            (['baz', '--baz', 'a'], {'sub_cmd': 'baz', 'bar': 'a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
