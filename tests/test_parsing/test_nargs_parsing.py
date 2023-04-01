#!/usr/bin/env python

from unittest import main

from cli_command_parser.commands import Command
from cli_command_parser.exceptions import UsageError
from cli_command_parser.parameters import Positional, Option, Flag
from cli_command_parser.testing import ParserTest


class NargsParsingTest(ParserTest):
    def test_positional_even_range(self):
        class Foo(Command):
            foo = Positional(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['a', 'b'], {'foo': ['a', 'b']}),
            (['a', 'b', 'c', 'd'], {'foo': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [[], ['a'], ['a', 'b', 'c'], ['a', 'b', 'c', 'd', 'e']]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_1_with_even_range_option(self):
        class Foo(Command):
            foo = Positional(nargs=1)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['z', '--bar', 'a', 'b'], {'foo': 'z', 'bar': ['a', 'b']}),
            (['z', '--bar', 'a', 'b', 'c', 'd'], {'foo': 'z', 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'z'], {'foo': 'z', 'bar': ['a', 'b']}),
            (['--bar', 'a', 'b', 'c', 'd', 'z'], {'foo': 'z', 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [
            [],
            ['z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b'],
            ['--bar', 'a', 'b', 'c', 'd'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_1_with_even_range_option_no_backtrack(self):
        class Foo(Command, allow_backtrack=False):
            foo = Positional(nargs=1)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['z', '--bar', 'a', 'b'], {'foo': 'z', 'bar': ['a', 'b']}),
            (['z', '--bar', 'a', 'b', 'c', 'd'], {'foo': 'z', 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'c', 'd', 'z'], {'foo': 'z', 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [
            [],
            ['z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b'],
            ['--bar', 'a', 'b', 'c', 'd'],
            ['--bar', 'a', 'b', 'z'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_2_with_even_range_option(self):
        class Foo(Command):
            foo = Positional(nargs=2)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['y', 'z', '--bar', 'a', 'b'], {'foo': ['y', 'z'], 'bar': ['a', 'b']}),
            (['y', 'z', '--bar', 'a', 'b', 'c', 'd'], {'foo': ['y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'y', 'z'], {'foo': ['y', 'z'], 'bar': ['a', 'b']}),
            (['--bar', 'a', 'b', 'c', 'd', 'y', 'z'], {'foo': ['y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [
            [],
            ['z', '--bar', 'a'],
            ['y', 'z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b'],
            ['y', 'z', '--bar', 'a', 'b', 'c'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a'],
            ['--bar', 'a', 'b'],
            ['--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b', 'c', 'd', 'e'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_2_with_even_range_option_no_backtrack(self):
        class Foo(Command, allow_backtrack=False):
            foo = Positional(nargs=2)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['y', 'z', '--bar', 'a', 'b'], {'foo': ['y', 'z'], 'bar': ['a', 'b']}),
            (['y', 'z', '--bar', 'a', 'b', 'c', 'd'], {'foo': ['y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'c', 'd', 'y', 'z'], {'foo': ['y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [
            [],
            ['z', '--bar', 'a'],
            ['y', 'z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b'],
            ['y', 'z', '--bar', 'a', 'b', 'c'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a'],
            ['--bar', 'a', 'b'],
            ['--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b', 'c', 'd', 'e'],
            ['--bar', 'a', 'b', 'y', 'z'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_3_with_even_range_option(self):
        class Foo(Command):
            foo = Positional(nargs=3)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['x', 'y', 'z', '--bar', 'a', 'b'], {'foo': ['x', 'y', 'z'], 'bar': ['a', 'b']}),
            (['x', 'y', 'z', '--bar', 'a', 'b', 'c', 'd'], {'foo': ['x', 'y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'x', 'y', 'z'], {'foo': ['x', 'y', 'z'], 'bar': ['a', 'b']}),
            (['--bar', 'a', 'b', 'c', 'd', 'x', 'y', 'z'], {'foo': ['x', 'y', 'z'], 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [
            [],
            ['z', '--bar', 'a'],
            ['y', 'z', '--bar', 'a'],
            ['x', 'y', 'z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b'],
            ['y', 'z', '--bar', 'a', 'b', 'c'],
            ['x', 'y', 'z', '--bar', 'a', 'b', 'c'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b', 'c'],
            ['--bar', 'a', 'b', 'c', 'd'],
            ['--bar', 'a', 'b', 'c', 'd', 'e', 'f'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_int_3_with_even_range_option(self):
        class Foo(Command):
            foo = Positional(nargs=3, type=int)
            bar = Option(nargs=range(2, 6, 2))  # 2 or 4

        success_cases = [
            (['1', '2', '3', '--bar', 'a', 'b'], {'foo': [1, 2, 3], 'bar': ['a', 'b']}),
            (['1', '2', '3', '--bar', 'a', 'b', 'c', 'd'], {'foo': [1, 2, 3], 'bar': ['a', 'b', 'c', 'd']}),
            (['--bar', 'a', 'b', 'c', 'd', '1', '2', '3'], {'foo': [1, 2, 3], 'bar': ['a', 'b', 'c', 'd']}),
        ]
        fail_cases = [[], ['--bar', 'a', 'b', '1', '2', '3']]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_pos_after_variable_nargs(self):
        for n in range(1, 4):

            class Foo(Command):
                foo = Positional(nargs=n)
                bar = Option(nargs='+')

            foo = ['a'] * n
            exp = 'a' if n == 1 else foo
            success_cases = [
                ([*foo, '--bar', 'w', 'x'], {'foo': exp, 'bar': ['w', 'x']}),
                ([*foo, '--bar', 'w', 'x', 'y', 'z'], {'foo': exp, 'bar': ['w', 'x', 'y', 'z']}),
                (['--bar', 'w', 'x', *foo], {'foo': exp, 'bar': ['w', 'x']}),
                (['--bar', 'w', 'x', 'y', 'z', *foo], {'foo': exp, 'bar': ['w', 'x', 'y', 'z']}),
            ]
            self.assert_parse_results_cases(Foo, success_cases)

    def test_pos_int_after_variable_nargs(self):
        class Foo(Command):
            foo = Positional(nargs=2, type=int)
            bar = Option(nargs='+')
            baz = Flag()

        success_cases = [
            (['1', '2', '--bar', 'a', 'b'], {'foo': [1, 2], 'bar': ['a', 'b'], 'baz': False}),
            (['1', '2', '--bar', 'a', 'b', 'c', 'd'], {'foo': [1, 2], 'bar': ['a', 'b', 'c', 'd'], 'baz': False}),
            (['--bar', 'a', 'b', '1', '2'], {'foo': [1, 2], 'bar': ['a', 'b'], 'baz': False}),
            (['--bar', 'a', 'b', 'c', 'd', '1', '2'], {'foo': [1, 2], 'bar': ['a', 'b', 'c', 'd'], 'baz': False}),
        ]
        fail_cases = [
            [],
            ['1'],
            ['--baz', '1'],
            ['z', '--bar', 'a'],
            ['y', 'z', '--bar', 'a'],
            ['z', '--bar', 'a', 'b'],
            ['y', 'z', '--bar', 'a', 'b', 'c'],
            ['z', '--bar', 'a', 'b', 'c'],
            ['--bar', 'a'],
            ['--bar', '1'],
            ['--bar', 'a', 'b'],
            ['--bar', '1', '2'],
            ['--bar', 'a', 'b', '1'],
            ['--bar', 'a', 'b', '1', 'd'],
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_defaults_with_nargs_multi(self):
        success_cases = [
            ([], {'bar': [1]}),
            (['-b', '2'], {'bar': [2]}),
            (['-b=2'], {'bar': [2]}),
            (['--bar', '2', '3'], {'bar': [2, 3]}),
        ]
        fail_cases = [
            ['-b=2', '3'],  # argparse also rejects this
            ['-b'],
        ]

        for default in (1, [1]):
            with self.subTest(default=default):

                class Foo(Command):
                    bar = Option('-b', nargs='+', type=int, default=default)

                self.assert_parse_results_cases(Foo, success_cases)
                self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
