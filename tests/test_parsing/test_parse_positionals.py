#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, REMAINDER, PassThru, Positional, Option, Flag
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import UsageError, BadArgument, NoSuchOption
from cli_command_parser.testing import ParserTest

get_config = CommandMeta.config


class PositionalTest(ParserTest):
    def test_extra_positional_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', 'baz'])

        get_config(Foo).ignore_unknown = True
        self.assertEqual(Foo.parse(['bar', 'baz']).ctx.remaining, ['baz'])

    def test_first_rejects_bad_choice(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))

        with self.assertRaises(BadArgument):
            Foo.parse(['c'])

    def test_multiple_positionals(self):
        class Foo(Command):
            bar = Positional(nargs=2)
            baz = Positional()

        self.assertEqual('append', Foo.bar._action_name)
        self.assert_parse_results(Foo, ['a', 'b', 'c'], {'bar': ['a', 'b'], 'baz': 'c'})
        fail_cases = [[], ['a', 'b', 'c', 'd'], ['a', 'b']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nargs_question_between_nargs_1_and_pass_thru(self):
        class Foo(Command):
            foo = Positional()
            bar = Positional(nargs='?')
            baz = PassThru()

        success_cases = [
            (['a', 'b'], {'foo': 'a', 'bar': 'b', 'baz': None}),
            (['a', 'b', '--', 'x'], {'foo': 'a', 'bar': 'b', 'baz': ['x']}),
            (['a', 'b', '--', 'x', 'y'], {'foo': 'a', 'bar': 'b', 'baz': ['x', 'y']}),
            (['a'], {'foo': 'a', 'bar': None, 'baz': None}),
            (['a', '--', 'x'], {'foo': 'a', 'bar': None, 'baz': ['x']}),
            (['a', '--'], {'foo': 'a', 'bar': None, 'baz': []}),
            (['a', '--', 'x', 'y'], {'foo': 'a', 'bar': None, 'baz': ['x', 'y']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [[], ['--', 'x'], ['a', 'b', 'c', '--', 'x']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_nargs_star_between_nargs_1_and_pass_thru(self):
        class Foo(Command):
            foo = Positional()
            bar = Positional(nargs='*')
            baz = PassThru()

        success_cases = [
            (['a', 'b'], {'foo': 'a', 'bar': ['b'], 'baz': None}),
            (['a', 'b', '--', 'x'], {'foo': 'a', 'bar': ['b'], 'baz': ['x']}),
            (['a', 'b', '--', 'x', 'y'], {'foo': 'a', 'bar': ['b'], 'baz': ['x', 'y']}),
            (['a', 'b', 'c', '--', 'x'], {'foo': 'a', 'bar': ['b', 'c'], 'baz': ['x']}),
            (['a', 'b', 'c', 'd', '--', 'x'], {'foo': 'a', 'bar': ['b', 'c', 'd'], 'baz': ['x']}),
            (['a'], {'foo': 'a', 'bar': [], 'baz': None}),
            (['a', '--', 'x'], {'foo': 'a', 'bar': [], 'baz': ['x']}),
            (['a', '--'], {'foo': 'a', 'bar': [], 'baz': []}),
            (['a', '--', 'x', 'y'], {'foo': 'a', 'bar': [], 'baz': ['x', 'y']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [[], ['--', 'x']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_seemingly_overlapping_choices(self):
        class Show(Command):
            type = Positional(choices=('foo', 'foo bar'))

        success_cases = [
            (['foo'], {'type': 'foo'}),
            (['foo bar'], {'type': 'foo bar'}),
        ]
        self.assert_parse_results_cases(Show, success_cases)
        # Only ChoiceMap splits/combines on space - `foo bar` must be provided as a single/quoted argument here
        self.assert_parse_fails(Show, ['foo', 'bar'])

    def test_positional_remainder(self):
        class Foo(Command):
            bar = Flag()
            baz = Positional(nargs='REMAINDER')

        success_cases = [
            (['--bar', 'a', 'b', '--c', '---x'], {'bar': True, 'baz': ['a', 'b', '--c', '---x']}),
            (['--bar', '--foo', 'a', '-b', 'c'], {'bar': True, 'baz': ['--foo', 'a', '-b', 'c']}),
            (['--bar', '--'], {'bar': True, 'baz': ['--']}),
            (['--', '--bar'], {'bar': False, 'baz': ['--', '--bar']}),
            (['--bar', '-1'], {'bar': True, 'baz': ['-1']}),
            (['-1', '--bar'], {'bar': False, 'baz': ['-1', '--bar']}),
            (['--bar', 'abc'], {'bar': True, 'baz': ['abc']}),
            (['abc', '--bar'], {'bar': False, 'baz': ['abc', '--bar']}),
            ([], {'bar': False, 'baz': []}),
            (['--bar'], {'bar': True, 'baz': []}),
            (['---bar'], {'bar': False, 'baz': ['---bar']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_positional_remainder_min_1(self):
        class Foo(Command):
            bar = Flag()
            baz = Positional(nargs=(1, REMAINDER), allow_leading_dash=True)

        success_cases = [
            (['--bar', 'a', 'b', '--c', '---x'], {'bar': True, 'baz': ['a', 'b', '--c', '---x']}),
            (['--bar', '--foo', 'a', '-b', 'c'], {'bar': True, 'baz': ['--foo', 'a', '-b', 'c']}),
            (['--bar', '--'], {'bar': True, 'baz': ['--']}),
            (['--', '--bar'], {'bar': False, 'baz': ['--', '--bar']}),
            (['--bar', '-1'], {'bar': True, 'baz': ['-1']}),
            (['-1', '--bar'], {'bar': False, 'baz': ['-1', '--bar']}),
            (['--bar', 'abc'], {'bar': True, 'baz': ['abc']}),
            (['abc', '--bar'], {'bar': False, 'baz': ['abc', '--bar']}),
            (['---bar'], {'bar': False, 'baz': ['---bar']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [[], ['--bar']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


class NargsParsingTest(ParserTest):
    # region Nargs = Even Range

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

    # endregion

    def test_pos_after_variable_nargs(self):
        for n in range(1, 4):

            class Foo(Command):
                foo = Positional(nargs=n, action='append')
                bar = Option(nargs='+')

            foo = ['a'] * n
            success_cases = [
                ([*foo, '--bar', 'w', 'x'], {'foo': foo, 'bar': ['w', 'x']}),
                ([*foo, '--bar', 'w', 'x', 'y', 'z'], {'foo': foo, 'bar': ['w', 'x', 'y', 'z']}),
                (['--bar', 'w', 'x', *foo], {'foo': foo, 'bar': ['w', 'x']}),
                (['--bar', 'w', 'x', 'y', 'z', *foo], {'foo': foo, 'bar': ['w', 'x', 'y', 'z']}),
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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
