#!/usr/bin/env python

from unittest import main

from cli_command_parser.commands import Command
from cli_command_parser.exceptions import NoSuchOption, BadArgument
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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
