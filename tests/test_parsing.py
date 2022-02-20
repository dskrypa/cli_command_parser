#!/usr/bin/env python

from dataclasses import dataclass
from unittest import main

from command_parser.commands import Command
from command_parser.exceptions import NoSuchOption, BadArgument, ParamsMissing, UsageError, MissingArgument
from command_parser.parameters import Positional, Option, Flag
from command_parser.testing import ParserTest


class ParamComboTest(ParserTest):
    def test_flag_and_option(self):
        class Ipython(Command):
            interactive = Flag('-i')
            module = Option('-m')

        success_cases = [
            (['-im', 'lib.command_parser'], {'interactive': True, 'module': 'lib.command_parser'}),
            (['-i', '-m', 'lib.command_parser'], {'interactive': True, 'module': 'lib.command_parser'}),
            (['-m', 'lib.command_parser'], {'interactive': False, 'module': 'lib.command_parser'}),
        ]
        self.assert_parse_results_cases(Ipython, success_cases)

    def test_pos_after_optional(self):
        class Foo(Command, error_handler=None):
            cmd = Positional(help='The command to perform')
            id = Positional(help='The ID to act upon')
            auth = Option('-a', choices=('a', 'b'), help='Auth mode')

        foo = self.assert_parse_results(Foo, ['foo', '-a', 'b', 'bar'], {'cmd': 'foo', 'id': 'bar', 'auth': 'b'})
        self.assertIn('cmd', foo.args)
        self.assertIn(Foo.cmd, foo.args)
        self.assertNotIn('bar', foo.args)

        with self.assertRaises(ParamsMissing):
            Foo.parse_and_run(['foo', '-a', 'b'])

    def test_combined_flags(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        success_cases = [
            (['-fb'], {'foo': True, 'bar': True}),
            (['-bf'], {'foo': True, 'bar': True}),
            (['-f'], {'foo': True, 'bar': False}),
            (['-b'], {'foo': False, 'bar': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)


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


class OptionTest(ParserTest):
    def test_triple_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['---'], ['---bar'], ['--bar', '---'], ['--bar', '---bar']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_misc_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['----'], ['----bar'], ['--bar', '----'], ['--bar', '----bar'], ['-'], ['--bar', '-']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_extra_long_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz'])

        foo = Foo.parse(['bar', '--baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz', 'a'])

        foo = Foo.parse(['bar', '--baz', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz', 'a'])

    def test_extra_short_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b'])

        foo = Foo.parse(['bar', '-b'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b', 'a'])

        foo = Foo.parse(['bar', '-b', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b', 'a'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b=a'])

        foo = Foo.parse(['bar', '-b=a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b=a'])

    def test_short_value_invalid(self):
        class Foo(Command):
            foo = Flag()
            bar = Option()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--bar', '-f'])

    def test_short_value_no_space(self):
        class Foo(Command):
            bar = Option('-b')

        self.assert_parse_results(Foo, ['-bar'], {'bar': 'ar'})

    def test_short_value_ambiguous(self):
        class Foo(Command):
            foo = Option('-f')
            foobar = Option('-foobar')
            foorab = Option('-foorab')

        success_cases = [
            ([], {'foo': None, 'foobar': None, 'foorab': None}),
            (['-f', 'a'], {'foo': 'a', 'foobar': None, 'foorab': None}),
            (['-fa'], {'foo': 'a', 'foobar': None, 'foorab': None}),
            (['-foo'], {'foo': 'oo', 'foobar': None, 'foorab': None}),
            (['-foa'], {'foo': 'oa', 'foobar': None, 'foorab': None}),
            (['-fooa'], {'foo': 'ooa', 'foobar': None, 'foorab': None}),
            (['-fooba'], {'foo': 'ooba', 'foobar': None, 'foorab': None}),
            (['-foora'], {'foo': 'oora', 'foobar': None, 'foorab': None}),
            (['-foobar', 'a'], {'foo': None, 'foobar': 'a', 'foorab': None}),
            (['-foorab', 'a'], {'foo': None, 'foobar': None, 'foorab': 'a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [
            (['-f'], MissingArgument),
            (['-foo', 'a'], UsageError),
            (['--foo'], MissingArgument),
            (['-foobar'], MissingArgument),
            (['--foobar'], MissingArgument),
            (['-foorab'], MissingArgument),
            (['--foorab'], MissingArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

    def test_custom_type_starting_with_dash(self):
        @dataclass
        class TimeOffset:
            value: str

        class Foo(Command):
            action = Positional()
            time: TimeOffset = Option('-t')

        success_cases = [
            (['a', '-t', '-h@h'], {'action': 'a', 'time': TimeOffset('-h@h')}),
            (['a', '--time', '-h@h'], {'action': 'a', 'time': TimeOffset('-h@h')}),
            (['a', '-t', '-2h@h'], {'action': 'a', 'time': TimeOffset('-2h@h')}),
            (['a', '--time', '-2h@h'], {'action': 'a', 'time': TimeOffset('-2h@h')}),
            (['a', '-t', '@h'], {'action': 'a', 'time': TimeOffset('@h')}),
            (['a', '--time', '@h'], {'action': 'a', 'time': TimeOffset('@h')}),
            (['a', '-t', '@h-5m'], {'action': 'a', 'time': TimeOffset('@h-5m')}),
            (['a', '--time', '@h-5m'], {'action': 'a', 'time': TimeOffset('@h-5m')}),
            (['a', '-t', '@h+5m'], {'action': 'a', 'time': TimeOffset('@h+5m')}),
            (['a', '--time', '@h+5m'], {'action': 'a', 'time': TimeOffset('@h+5m')}),
            (['a', '-t', 'now'], {'action': 'a', 'time': TimeOffset('now')}),
            (['a', '--time', 'now'], {'action': 'a', 'time': TimeOffset('now')}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [
            (['-h@h'], NoSuchOption),
            (['-2h@h'], NoSuchOption),
            (['a', '-t'], MissingArgument),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)


class PositionalTest(ParserTest):
    def test_extra_positional_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', 'baz'])

        foo = Foo.parse(['bar', 'baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['baz'])

    def test_first_rejects_bad_choice(self):
        class Foo(Command):
            bar = Positional(choices=('a', 'b'))

        with self.assertRaises(BadArgument):
            Foo.parse(['c'])


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
