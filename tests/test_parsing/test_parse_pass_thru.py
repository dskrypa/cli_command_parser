#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, Positional, SubCommand, PassThru, NoSuchOption, ParamsMissing
from cli_command_parser.testing import ParserTest


class PassThruTest(ParserTest):
    def test_sub_cmd_pass_thru_accepted(self):
        class Foo(Command):
            sub = SubCommand()

        class Bar(Foo):
            bar = Positional(choices=('a', 'b'))
            baz = PassThru()

        self.assert_parse_results(Foo, ['bar', 'a', '--', 'x'], {'sub': 'bar', 'bar': 'a', 'baz': ['x']})

    def test_sub_cmd_no_pass_thru_rejected(self):
        class Foo(Command):
            sub = SubCommand()

        class Bar(Foo):
            bar = Positional(choices=('a', 'b'))

        self.assert_parse_fails(Foo, ['bar', 'a', '--', 'x'], NoSuchOption)

    def test_required_pass_thru(self):
        class Foo(Command):
            bar = PassThru(required=True)

        success_cases = [
            (['--', 'a', 'b'], {'bar': ['a', 'b']}),
            (['--'], {'bar': []}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails(Foo, [], ParamsMissing)

    def test_positional_remainder_pass_thru_combo(self):
        class Foo(Command):
            bar = PassThru()
            baz = Positional(nargs='REMAINDER')

        success_cases = [
            (['--bar', 'a', 'b', '--c', '---x'], {'bar': None, 'baz': ['--bar', 'a', 'b', '--c', '---x']}),
            (['--bar', '--foo', 'a', '-b', 'c'], {'bar': None, 'baz': ['--bar', '--foo', 'a', '-b', 'c']}),
            (['--bar', '--'], {'bar': [], 'baz': ['--bar']}),  # PassThru is evaluated before all other params
            (['--bar', '--', 'abc'], {'bar': ['abc'], 'baz': ['--bar']}),
            (['--bar', '--', '-1'], {'bar': ['-1'], 'baz': ['--bar']}),
            (['--', '--bar'], {'bar': ['--bar'], 'baz': []}),
            (['--bar', '-1'], {'bar': None, 'baz': ['--bar', '-1']}),
            (['-1', '--bar'], {'bar': None, 'baz': ['-1', '--bar']}),
            (['--bar', 'abc'], {'bar': None, 'baz': ['--bar', 'abc']}),
            (['abc', '--bar'], {'bar': None, 'baz': ['abc', '--bar']}),
            (['abc', 'bar'], {'bar': None, 'baz': ['abc', 'bar']}),
            ([], {'bar': None, 'baz': []}),
            (['--'], {'bar': [], 'baz': []}),
            (['--bar'], {'bar': None, 'baz': ['--bar']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
