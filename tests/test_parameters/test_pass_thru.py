#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, CommandDefinitionError, Context, SubCommand, PassThru, Flag
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import NoSuchOption, ParamUsageError, MissingArgument, ParamsMissing
from cli_command_parser.testing import ParserTest


class PassThruTest(ParserTest):
    def test_pass_thru(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru()

        success_cases = [
            (['--bar', '--', 'a', 'b', '--c', '---x'], {'bar': True, 'baz': ['a', 'b', '--c', '---x']}),
            (['--', '--bar', '--', 'a', '-b', 'c'], {'bar': False, 'baz': ['--bar', '--', 'a', '-b', 'c']}),
            (['--bar', '--'], {'bar': True, 'baz': []}),
            (['--', '--bar'], {'bar': False, 'baz': ['--bar']}),
            (['--'], {'bar': False, 'baz': []}),
            (['--bar'], {'bar': True, 'baz': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_pass_thru_missing(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru(required=True)

        self.assertTrue(Foo.baz.default is not None)
        foo = Foo()
        with self.assert_raises_contains_str(ParamsMissing, "missing pass thru args separated from others with '--'"):
            foo.parse([])
        with self.assertRaises(MissingArgument):
            foo.baz  # noqa

    def test_multiple_rejected(self):
        class Foo(Command):
            bar = PassThru()
            baz = PassThru()

        with self.assert_raises_contains_str(CommandDefinitionError, 'it cannot follow another PassThru param'):
            Foo.parse([])

    def test_double_dash_without_pass_thru_rejected(self):
        class Foo(Command):
            bar = Flag()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--'])

    def test_parser_has_pass_thru(self):
        class Foo(Command):
            pt = PassThru()

        class Bar(Foo):
            pass

        self.assertTrue(get_params(Bar).pass_thru)

    def test_sub_cmd_multiple_rejected(self):
        class Foo(Command):
            sub = SubCommand()
            pt1 = PassThru()

        class Bar(Foo):
            pt2 = PassThru()

        with self.assert_raises_contains_str(CommandDefinitionError, 'it cannot follow another PassThru param'):
            Bar.parse([])

    def test_extra_rejected(self):
        with Context():
            pt = PassThru()
            pt.action.add_values(['a'])
            with self.assertRaises(ParamUsageError):
                pt.action.add_values(['a'])

    def test_usage(self):
        self.assertEqual('[-- FOO]', PassThru(name='foo', required=False).formatter.format_basic_usage())
        self.assertEqual('-- FOO', PassThru(name='foo', required=True).formatter.format_basic_usage())

    # region Unsupported Kwargs

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(choices=(1, 2))

    def test_allow_leading_dash_not_allowed(self):
        with self.assertRaises(TypeError):
            PassThru(allow_leading_dash=True)

    # endregion


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
