#!/usr/bin/env python

from unittest import main

from cli_command_parser import Command, Option, Flag, Positional, SubCommand, REMAINDER, BaseOption, ctx
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import UsageError, NoSuchOption, MissingArgument, AmbiguousShortForm, AmbiguousCombo
from cli_command_parser.nargs import Nargs
from cli_command_parser.parameters.base import parameter_action
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

        fail_cases = [['----'], ['----bar'], ['--bar', '----'], ['--bar', '----bar'], ['-'], ['--bar', '-'], ['---bar']]
        self.assert_parse_fails_cases(Foo, fail_cases, NoSuchOption)

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

    def test_short_value_ambiguous_permissive(self):
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

    def test_short_value_ambiguous_strict(self):
        class Foo(Command, ambiguous_short_combos='strict'):
            foo = Option('-f')
            foobar = Option('-foobar')
            foorab = Option('-foorab')

        with self.assertRaises(AmbiguousShortForm):
            Foo.parse([])

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

    def test_option_remainder(self):
        class Foo(Command):
            bar = Flag()
            baz = Option(nargs=(1, REMAINDER))

        success_cases = [
            (['--bar', '--baz', 'a', 'b', '--c', '---x'], {'bar': True, 'baz': ['a', 'b', '--c', '---x']}),
            (['--bar', '--baz', '--foo', 'a', '-b', 'c'], {'bar': True, 'baz': ['--foo', 'a', '-b', 'c']}),
            (['--bar', '--baz', '--'], {'bar': True, 'baz': ['--']}),
            (['--baz', '--', '--bar'], {'bar': False, 'baz': ['--', '--bar']}),
            (['--bar', '--baz', '-1'], {'bar': True, 'baz': ['-1']}),
            (['--baz', '-1', '--bar'], {'bar': False, 'baz': ['-1', '--bar']}),
            (['--bar', '--baz', 'abc'], {'bar': True, 'baz': ['abc']}),
            (['--baz', 'abc', '--bar'], {'bar': False, 'baz': ['abc', '--bar']}),
            ([], {'bar': False, 'baz': []}),
            (['--bar'], {'bar': True, 'baz': []}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-1', '--bar']]
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

    def test_2c_short_in_sub_cmd_with_base_1c_short_prefix(self):
        class Foo(Command):
            sub = SubCommand()
            foo = Option('-f')

        class Bar(Foo):
            foobar = Option('-fb')

        success_cases = [
            (['bar'], {'sub': 'bar', 'foo': None, 'foobar': None}),
            (['bar', '-fx'], {'sub': 'bar', 'foo': 'x', 'foobar': None}),
            (['bar', '-f=x'], {'sub': 'bar', 'foo': 'x', 'foobar': None}),
            (['bar', '-f', 'x'], {'sub': 'bar', 'foo': 'x', 'foobar': None}),
            (['bar', '--foo', 'x'], {'sub': 'bar', 'foo': 'x', 'foobar': None}),
            (['bar', '-fb=x'], {'sub': 'bar', 'foo': None, 'foobar': 'x'}),
            (['bar', '-fb', 'x'], {'sub': 'bar', 'foo': None, 'foobar': 'x'}),
            (['bar', '--foobar', 'x'], {'sub': 'bar', 'foo': None, 'foobar': 'x'}),
            (['bar', '-fb', 'x', '-f', 'y'], {'sub': 'bar', 'foo': 'y', 'foobar': 'x'}),
            (['bar', '-f', 'y', '-fb', 'x'], {'sub': 'bar', 'foo': 'y', 'foobar': 'x'}),
            (['bar', '-f=x', '-fb=y'], {'sub': 'bar', 'foo': 'x', 'foobar': 'y'}),
            (['bar', '-fb=y', '-f=x'], {'sub': 'bar', 'foo': 'x', 'foobar': 'y'}),
            (['bar', '--foobar', 'y', '--foo', 'x'], {'sub': 'bar', 'foo': 'x', 'foobar': 'y'}),
            (['bar', '--foo', 'x', '--foobar', 'y'], {'sub': 'bar', 'foo': 'x', 'foobar': 'y'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['bar', '-fby'], ['bar', '-fbx'], ['bar', '-fbar']]
        self.assert_parse_fails_cases(Foo, fail_cases, AmbiguousCombo)

    def test_action_append_default_nargs(self):
        class Foo(Command):
            bar = Option('-b', action='append')

        success_cases = [
            ([], {'bar': []}),
            (['-b', 'a'], {'bar': ['a']}),
            (['-b', 'a', '-b', 'b'], {'bar': ['a', 'b']}),
            (['-b', 'a', 'b'], {'bar': ['a', 'b']}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['-b']]
        self.assert_argv_parse_fails_cases(Foo, fail_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
