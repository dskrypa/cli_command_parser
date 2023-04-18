#!/usr/bin/env python

from abc import ABC
from unittest import main

from cli_command_parser import Command, Positional, Option, Flag, SubCommand, CommandDefinitionError
from cli_command_parser.exceptions import NoSuchOption, ParamsMissing, UsageError, ParamUsageError
from cli_command_parser.testing import ParserTest


class ParamComboTest(ParserTest):
    def test_pos_after_optional(self):
        class Foo(Command, error_handler=None):
            cmd = Positional(help='The command to perform')
            id = Positional(help='The ID to act upon')
            auth = Option('-a', choices=('a', 'b'), help='Auth mode')

        foo = self.assert_parse_results(Foo, ['foo', '-a', 'b', 'bar'], {'cmd': 'foo', 'id': 'bar', 'auth': 'b'})
        self.assertIn('cmd', foo.ctx)
        self.assertIn(Foo.cmd, foo.ctx)
        self.assertNotIn('bar', foo.ctx)

        with self.assertRaises(ParamsMissing):
            Foo.parse_and_run(['foo', '-a', 'b'])

    def test_multi_value_opt_with_positional(self):
        class Foo(Command):
            bar = Option(nargs=2)
            baz = Positional()

        self.assertEqual('append', Foo.bar.action)
        success_cases = [
            (['--bar', 'a', 'b', 'c'], {'bar': ['a', 'b'], 'baz': 'c'}),
            (['c', '--bar', 'a', 'b'], {'bar': ['a', 'b'], 'baz': 'c'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            [],
            ['a', 'b'],
            ['c', 'd', '--bar', 'a', 'b'],
            ['c', '--bar', 'a'],
            ['--bar', 'a', 'b', 'c', 'd'],
            ['--bar', 'a', 'b', '-baz'],
        ]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_positional_after_var_nargs(self):
        class Foo(Command):
            foo = Positional()
            bar = Option('-b', nargs=(2, 3), choices=('a', 'b', 'c'))

        success_cases = [
            (['--bar', 'a', 'b', 'd'], {'foo': 'd', 'bar': ['a', 'b']}),
            (['--bar', 'b', 'c', 'a', 'd'], {'foo': 'd', 'bar': ['b', 'c', 'a']}),
            (['d', '--bar', 'a', 'b'], {'foo': 'd', 'bar': ['a', 'b']}),
            (['d', '--bar', 'b', 'c', 'a'], {'foo': 'd', 'bar': ['b', 'c', 'a']}),
            (['-b', 'c', 'b', 'z'], {'foo': 'z', 'bar': ['c', 'b']}),
            (['-b', 'c', 'b', 'a', 'z'], {'foo': 'z', 'bar': ['c', 'b', 'a']}),
            (['a', '-b', 'c', 'b'], {'foo': 'a', 'bar': ['c', 'b']}),
            (['a', '-b', 'c', 'b', 'a'], {'foo': 'a', 'bar': ['c', 'b', 'a']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [
            ['--bar', 'd'],
            ['--bar', 'a', 'd'],
            ['--bar', 'b', 'd', 'a'],
            ['d', '--bar', 'a'],
            ['d', '--bar', 'b'],
            ['d', '--bar'],
            ['d', '-b'],
        ]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nargs_unbound_ints_then_pos_str(self):
        class Foo(Command):
            foo = Positional(nargs='+')
            bar = Option('-b', nargs='+', type=int)

        success_cases = [
            (['-b', '1', '2', 'a'], {'bar': [1, 2], 'foo': ['a']}),
            (['-b', '1', '2', 'a', 'b'], {'bar': [1, 2], 'foo': ['a', 'b']}),
            (['a', '-b', '1', '2'], {'bar': [1, 2], 'foo': ['a']}),
            (['a', 'b', '-b', '1', '2'], {'bar': [1, 2], 'foo': ['a', 'b']}),
        ]
        fail_cases = [['-b', 'a'], ['a', '-b'], ['a', '-b', 'c']]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


class ParseParamsWithSubcommandsTest(ParserTest):
    def test_sub_cmd_optional_before_base_positional(self):
        class Foo(Command):
            foo = Positional()
            sub = SubCommand()

        class Bar(Foo):
            baz = Option('-b')

        expected_pattern = 'subcommand arguments must be provided after the subcommand'
        fail_cases = [
            (['a', '-b', 'c', 'bar'], ParamUsageError, expected_pattern),
            (['a', '--baz', 'c', 'bar'], ParamUsageError, expected_pattern),
            (['-b', 'a', 'b', 'bar'], ParamUsageError, expected_pattern),
            (['--baz', 'a', 'b', 'bar'], ParamUsageError, expected_pattern),
            (['a', 'bar', '-b', 'c', 'd'], NoSuchOption),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)
        success_cases = [
            (['a', 'bar', '-b', 'c'], {'foo': 'a', 'sub': 'bar', 'baz': 'c'}),
            (['a', 'bar'], {'foo': 'a', 'sub': 'bar', 'baz': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_nested_sub_cmd_optional_before_base_positional(self):
        class Foo(Command):
            sub_a = SubCommand()

        class Bar(Foo):
            sub_b = SubCommand()

        class Baz(Bar):
            foo = Option('-f')
            bar = Flag('-b')

        expected_pattern = 'subcommand arguments must be provided after the subcommand'
        fail_cases = [
            (['bar', '-f', 'c', 'baz'], ParamUsageError, expected_pattern),
            (['bar', '--foo', 'c', 'baz'], ParamUsageError, expected_pattern),
            (['-f', 'c', 'bar', 'baz'], ParamUsageError, expected_pattern),
            (['--foo', 'c', 'bar', 'baz'], ParamUsageError, expected_pattern),
            (['a', 'bar', '-f', 'c', 'd'], UsageError),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

        success_cases = [
            (['bar', 'baz', '-f', 'c'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': False}),
            (['bar', 'baz', '--foo', 'c'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': False}),
            (['bar', 'baz'], {'foo': None, 'sub_a': 'bar', 'sub_b': 'baz', 'bar': False}),
            (['bar', 'baz', '-f', 'c', '-b'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
            (['bar', 'baz', '-b'], {'foo': None, 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
            (['bar', 'baz', '--bar'], {'foo': None, 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
            (['-b', 'bar', 'baz', '-f', 'c'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
            (['--bar', 'bar', 'baz', '-f', 'c'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
            (['bar', '-b', 'baz', '-f', 'c'], {'foo': 'c', 'sub_a': 'bar', 'sub_b': 'baz', 'bar': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_common_positional_after_sub_command(self):
        class Foo(Command):
            sub = SubCommand()
            pos = Positional()

        class Bar(Foo):
            bar = Option('-b')

        class Baz(Foo):
            baz = Option('-b')

        bar_expected = {'pos': 'a', 'sub': 'bar', 'bar': 'c'}
        baz_expected = {'pos': 'a', 'sub': 'baz', 'baz': 'c'}
        success_cases = [
            (['bar', 'a', '-b', 'c'], bar_expected),
            (['bar', '-b', 'c', 'a'], bar_expected),
            (['baz', 'a', '-b', 'c'], baz_expected),
            (['baz', '-b', 'c', 'a'], baz_expected),
            (['bar', 'a'], {'pos': 'a', 'sub': 'bar', 'bar': None}),
            (['baz', 'a'], {'pos': 'a', 'sub': 'baz', 'baz': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        # fmt: off
        fail_cases = [
            ['a', 'bar'], ['a', 'baz'], ['baz'], ['bar'], ['a'], ['-b', 'c', 'bar'], ['-b', 'c', 'baz'], ['-b', 'c'],
            ['-b', 'c', 'bar', 'a'], ['-b', 'c', 'baz', 'a'], [],
        ]
        # fmt: on
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_in_one_sub_cmd(self):
        class Cmd(Command):
            sub = SubCommand()
            pre = Positional()

        class Foo(Cmd):
            foo = Positional()
            bar = Option('-b')

        class Bar(Cmd):
            baz = Option('-b')

        foo_expected = {'pre': 'a', 'sub': 'foo', 'bar': 'c', 'foo': '2'}
        bar_expected = {'pre': 'a', 'sub': 'bar', 'baz': 'c'}
        success_cases = [
            (['foo', 'a', '2', '-b', 'c'], foo_expected),
            (['foo', 'a', '-b', 'c', '2'], foo_expected),
            (['foo', '-b', 'c', 'a', '2'], foo_expected),
            (['bar', 'a', '-b', 'c'], bar_expected),
            (['bar', '-b', 'c', 'a'], bar_expected),
            (['foo', 'x', '2'], {'pre': 'x', 'sub': 'foo', 'bar': None, 'foo': '2'}),
            (['bar', 'x'], {'pre': 'x', 'sub': 'bar', 'baz': None}),
        ]
        self.assert_parse_results_cases(Cmd, success_cases)
        # fmt: off
        fail_cases = [
            ['a', 'bar'], ['a', 'foo'], ['foo'], ['bar'], ['a'], ['-b', 'c', 'bar'], ['-b', 'c', 'foo'], ['-b', 'c'],
            ['-b', 'c', 'bar', 'a'], ['-b', 'c', 'foo', 'a'], ['foo', '-b', 'c', 'a'], ['foo', 'x'], [],
        ]
        # fmt: on
        self.assert_parse_fails_cases(Cmd, fail_cases, UsageError)

    def test_middle_abc_subcommand_positional_basic(self):
        class Base(Command):
            sub = SubCommand()
            pre = Positional()

        class Mid(Base, ABC):
            mid = Positional()

        class A(Mid):
            bar = Flag('-b')

        success_cases = [
            (['a', '1', '2', '-b'], {'sub': 'a', 'pre': '1', 'mid': '2', 'bar': True}),
            (['a', '1', '-b', '2'], {'sub': 'a', 'pre': '1', 'mid': '2', 'bar': True}),
            (['a', '-b', '1', '2'], {'sub': 'a', 'pre': '1', 'mid': '2', 'bar': True}),
            (['a', 'b', 'c'], {'sub': 'a', 'pre': 'b', 'mid': 'c', 'bar': False}),
            (['-b', 'a', 'b', 'c'], {'sub': 'a', 'pre': 'b', 'mid': 'c', 'bar': True}),
        ]
        self.assert_parse_results_cases(Base, success_cases)
        fail_cases = [[], ['a'], ['a', 'b']]
        self.assert_parse_fails_cases(Base, fail_cases, UsageError)

    def test_no_sub_cmds(self):
        class Cmd(Command):
            sub = SubCommand()
            pre = Positional()

        with self.assertRaisesRegex(CommandDefinitionError, 'has no sub Commands'):
            Cmd.parse([])


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
