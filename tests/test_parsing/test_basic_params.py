#!/usr/bin/env python

from unittest import main

from cli_command_parser.commands import Command
from cli_command_parser.context import ctx
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import NoSuchOption, BadArgument, ParamsMissing, UsageError, MissingArgument
from cli_command_parser.nargs import Nargs
from cli_command_parser.parameters.base import BaseOption, parameter_action
from cli_command_parser.parameters import Positional, Option, Flag, SubCommand, PassThru
from cli_command_parser.testing import ParserTest

get_config = CommandMeta.config


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

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz', 'a'])

        get_config(Foo).ignore_unknown = True
        self.assertEqual(Foo.parse(['bar', '--baz']).ctx.remaining, ['--baz'])
        self.assertEqual(Foo.parse(['bar', '--baz', 'a']).ctx.remaining, ['--baz', 'a'])

    def test_extra_short_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        fail_cases = [['bar', '-b'], ['bar', '-b', 'a'], ['bar', '-b=a']]
        self.assert_parse_fails_cases(Foo, fail_cases, NoSuchOption)

        get_config(Foo).ignore_unknown = True
        self.assertEqual(Foo.parse(['bar', '-b']).ctx.remaining, ['-b'])
        self.assertEqual(Foo.parse(['bar', '-b', 'a']).ctx.remaining, ['-b', 'a'])
        self.assertEqual(Foo.parse(['bar', '-b=a']).ctx.remaining, ['-b=a'])

    def test_short_value_invalid(self):
        class Foo(Command):
            foo = Flag()
            bar = Option()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--bar', '-f'])

    def test_short_value_no_space(self):
        class Foo(Command):
            foo = Option('-f')
            bar = Option('-b')

        success_cases = [
            (['-bar'], {'bar': 'ar', 'foo': None}),
            (['-btest'], {'bar': 'test', 'foo': None}),
            (['-ftest'], {'foo': 'test', 'bar': None}),
            (['-b-'], {'bar': '-', 'foo': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

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
        class TimeOffset:
            def __init__(self, value: str):
                self.value = value

            def __eq__(self, other):
                return self.value == other.value

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

    def test_nargs_question(self):
        class CustomOption(BaseOption):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, action='store', **kwargs)
                self.nargs = Nargs('?')

            @parameter_action
            def store(self, value):
                ctx.set_parsed_value(self, value)

        class Foo(Command):
            bar = CustomOption('-b')

        success_cases = [
            ([], {'bar': None}),
            (['--bar'], {'bar': None}),
            (['--bar', 'a'], {'bar': 'a'}),
            (['--bar=a'], {'bar': 'a'}),
            (['-b'], {'bar': None}),
            (['-b', 'a'], {'bar': 'a'}),
            (['-b=a'], {'bar': 'a'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_underscore_dash_swap_allowed(self):
        class Foo(Command, option_name_mode='both'):
            foo_bar = Flag()

        success_cases = [(['--foo-bar'], {'foo_bar': True}), (['--foo_bar'], {'foo_bar': True})]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-foo-bar'], ['-foo_bar'], ['--foobar'], ['--fooBar']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

    def test_dash_only(self):
        class Foo(Command, option_name_mode='dash'):
            foo_bar = Flag()

        success_cases = [(['--foo-bar'], {'foo_bar': True})]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-foo-bar'], ['-foo_bar'], ['--foobar'], ['--fooBar'], ['--foo_bar']]
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)


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

        self.assertEqual('append', Foo.bar.action)
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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
