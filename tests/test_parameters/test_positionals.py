#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, ParamGroup, SubCommand, Positional
from cli_command_parser.exceptions import ParameterDefinitionError, CommandDefinitionError, UsageError
from cli_command_parser.parameters.base import parameter_action, BasePositional
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

    def test_unbound_nargs_defaults(self):
        for nargs in ('*', 'REMAINDER'):
            for default in ('a', ['a']):
                with self.subTest(nargs=nargs, default=default):

                    class Foo(Command):
                        bar = Positional(nargs=nargs, default=default)

                    success_cases = [([], {'bar': ['a']}), (['b'], {'bar': ['b']}), (['a', 'b'], {'bar': ['a', 'b']})]
                    self.assert_parse_results_cases(Foo, success_cases)

    def test_pos_after_unbound_nargs_rejected(self):
        expected_msg = 'it accepts a variable number of arguments with no specific choices defined'
        for nargs in ('+', '*', 'REMAINDER'):
            with self.subTest(nargs=nargs):

                class Foo(Command):
                    bar = Positional(nargs=nargs)
                    baz = Positional()

                with self.assertRaisesRegex(CommandDefinitionError, expected_msg):
                    Foo.parse([])

    def test_sub_cmd_pos_after_unbound_nargs_rejected(self):
        expected_msg = 'it accepts a variable number of arguments with no specific choices defined'
        for nargs in ('+', '*', 'REMAINDER'):
            with self.subTest(nargs=nargs):

                class Foo(Command):
                    sub = SubCommand()
                    bar = Positional(nargs=nargs)

                class Bar(Foo):
                    baz = Positional()

                with self.assertRaisesRegex(CommandDefinitionError, expected_msg):
                    Foo.parse(['bar'])

    def test_pos_grouped_pos_both_required(self):
        class Foo(Command):
            bar = Positional()
            with ParamGroup():
                baz = Positional()

        success_cases = [(['a', 'b'], {'bar': 'a', 'baz': 'b'})]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [[], ['a']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_type_annotation_with_remainder_ignored(self):
        class Foo(Command):
            bar: int = Positional(nargs='REMAINDER')

        self.assertIsNone(Foo.bar.type)  # noqa

    def test_type_with_remainder_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Type casting and choices are not supported'):

            class Foo(Command):
                bar = Positional(nargs='REMAINDER', type=int)

    def test_choices_with_remainder_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Type casting and choices are not supported'):

            class Foo(Command):
                bar = Positional(nargs='REMAINDER', choices=('a', 'b'))

    def test_bad_leading_dash_with_remainder_rejected(self):
        expected = 'only allow_leading_dash=AllowLeadingDash.ALWAYS'
        for allow_leading_dash in ('numeric', False):
            with self.subTest(allow_leading_dash=allow_leading_dash):
                with self.assertRaisesRegex(ParameterDefinitionError, expected):

                    class Foo(Command):
                        bar = Positional(nargs='REMAINDER', allow_leading_dash=allow_leading_dash)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
