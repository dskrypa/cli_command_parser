#!/usr/bin/env python

from unittest import main

from cli_command_parser.commands import Command
from cli_command_parser.exceptions import NoSuchOption, BadArgument, UsageError
from cli_command_parser.parameters import Positional, Option
from cli_command_parser.testing import ParserTest


class NumericValueTest(ParserTest):
    def test_int_option(self):
        class Foo(Command, error_handler=None):
            bar: int = Option()

        self.assertEqual(-1, Foo.parse(['--bar', '-1']).bar)
        fail_cases = [
            (['--bar', '-1.5'], NoSuchOption),
            (['--bar', '1.5'], BadArgument),
            (['--bar', 'a'], BadArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_int_positional(self):
        class Foo(Command, error_handler=None):
            bar: int = Positional()

        self.assertEqual(-1, Foo.parse(['-1']).bar)
        fail_cases = [
            (['-1.5'], NoSuchOption),
            (['1.5'], BadArgument),
            (['-1.5.1'], NoSuchOption),
            (['1.5.1'], BadArgument),
            (['a'], BadArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_float_option(self):
        class Foo(Command, error_handler=None):
            bar: float = Option()

        success_cases = [
            (['--bar', '1'], {'bar': 1}),
            (['--bar', '-1'], {'bar': -1}),
            (['--bar', '1.5'], {'bar': 1.5}),
            (['--bar', '-1.5'], {'bar': -1.5}),
            (['--bar', '0'], {'bar': 0}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            (['--bar', '-1.5.1'], NoSuchOption),
            (['--bar', '1.5.1'], BadArgument),
            (['--bar', 'a'], BadArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_float_positional(self):
        class Foo(Command, error_handler=None):
            bar: float = Positional()

        success_cases = [
            (['1'], {'bar': 1}),
            (['-1'], {'bar': -1}),
            (['1.5'], {'bar': 1.5}),
            (['-1.5'], {'bar': -1.5}),
            (['0'], {'bar': 0}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            (['-1.5.1'], NoSuchOption),
            (['1.5.1'], BadArgument),
            (['a'], BadArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)


class LeadingDashValueTest(ParserTest):
    def test_str_option(self):
        class Foo(Command, error_handler=None):
            bar = Option()

        success_cases = [
            (['--bar', '1'], {'bar': '1'}),
            (['--bar', '-1'], {'bar': '-1'}),
            (['--bar', '1.5'], {'bar': '1.5'}),
            (['--bar', '-1.5'], {'bar': '-1.5'}),
            (['--bar', '1.5.1'], {'bar': '1.5.1'}),
            (['--bar', '0'], {'bar': '0'}),
            (['--bar', 'a'], {'bar': 'a'}),
            (['--bar', 'a b'], {'bar': 'a b'}),
            (['--bar', ' -a'], {'bar': ' -a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            (['-a'], NoSuchOption),
            (['--a'], NoSuchOption),
            (['--bar', '-a'], NoSuchOption),
            (['--bar', '-1.5.1'], NoSuchOption),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_allow_leading_dash(self):
        class Foo(Command):
            earliest = Option('-E', type=str.strip, allow_leading_dash='always')
            latest = Option('-L', allow_leading_dash=True)

        success_cases = [
            (['-E', '@h-5m', '-L', 'now'], {'earliest': '@h-5m', 'latest': 'now'}),
            (['-E', '1d@d', '-L', 'd@d'], {'earliest': '1d@d', 'latest': 'd@d'}),
            (['-E', '-5d@d', '-L', '-1d@d'], {'earliest': '-5d@d', 'latest': '-1d@d'}),
            (['-E', ' -5d@d', '-L', '-1d@d'], {'earliest': '-5d@d', 'latest': '-1d@d'}),
            ([], {'earliest': None, 'latest': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_leading_dash_misc(self):
        class Foo(Command):
            bar = Positional(allow_leading_dash='ALWAYS')
            baz = Option('-b', allow_leading_dash=False)

        success_cases = [
            (['-1'], {'bar': '-1', 'baz': None}),
            (['-1', '-b', 'a'], {'bar': '-1', 'baz': 'a'}),
            (['-b', 'a', '-1'], {'bar': '-1', 'baz': 'a'}),
            (['-b', 'a', '1'], {'bar': '1', 'baz': 'a'}),
            (['--baz', 'a', '-1'], {'bar': '-1', 'baz': 'a'}),
            (['--baz', 'a', '1'], {'bar': '1', 'baz': 'a'}),
            (['-x'], {'bar': '-x', 'baz': None}),
            (['-x', '-b', 'a'], {'bar': '-x', 'baz': 'a'}),
            (['-b', 'a', '-x'], {'bar': '-x', 'baz': 'a'}),
            (['-b', 'a', 'x'], {'bar': 'x', 'baz': 'a'}),
            (['--baz', 'a', '-x'], {'bar': '-x', 'baz': 'a'}),
            (['--baz', 'a', 'x'], {'bar': 'x', 'baz': 'a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [
            ['-b'],
            ['--baz'],
            ['--bar'],
            ['-1', '-2'],
            ['-1', '-b', '-2'],
            ['x', '-b', '-2'],
            ['x', '-b', '-y'],
        ]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
