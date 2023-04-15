#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, ParamGroup
from cli_command_parser.exceptions import ParameterDefinitionError, CommandDefinitionError, UsageError
from cli_command_parser.parameters.base import parameter_action, BasePositional
from cli_command_parser.parameters import Positional
from cli_command_parser.testing import ParserTest


class PositionalTest(ParserTest):
    def test_required_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(required=False)

    def test_default_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(default=None)

    def test_custom_default_rejected(self):
        class CustomPositional(BasePositional):
            foo = parameter_action(Mock())

        with self.assertRaises(ParameterDefinitionError):
            CustomPositional(default=None, action='foo')

    def test_nargs_0_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(nargs=0)

    def test_action_nargs_mismatch_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Positional(nargs=2, action='store')

        self.assertEqual(1, Positional(action='store').nargs)

    def test_nargs_star_empty_list(self):
        class Foo(Command):
            bar = Positional(nargs='*')

        success_cases = [([], {'bar': []}), (['a'], {'bar': ['a']}), (['a', 'b'], {'bar': ['a', 'b']})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_nargs_star_defaults(self):
        for default in ('a', ['a']):
            with self.subTest(default=default):

                class Foo(Command):
                    bar = Positional(nargs='*', default=default)

                success_cases = [([], {'bar': ['a']}), (['b'], {'bar': ['b']}), (['a', 'b'], {'bar': ['a', 'b']})]
                self.assert_parse_results_cases(Foo, success_cases)

    def test_pos_after_nargs_star_rejected(self):
        class Foo(Command):
            bar = Positional(nargs='*')
            baz = Positional()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    def test_pos_grouped_pos_both_required(self):
        class Foo(Command):
            bar = Positional()
            with ParamGroup():
                baz = Positional()

        success_cases = [(['a', 'b'], {'bar': 'a', 'baz': 'b'})]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [[], ['a']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
