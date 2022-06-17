#!/usr/bin/env python

from dataclasses import dataclass
from unittest import main, skip

from cli_command_parser.commands import Command
from cli_command_parser.context import ctx
from cli_command_parser.exceptions import (
    NoSuchOption,
    BadArgument,
    ParamsMissing,
    UsageError,
    MissingArgument,
    ParamUsageError,
)
from cli_command_parser.nargs import Nargs
from cli_command_parser.parameters import (
    Positional,
    Option,
    Flag,
    Counter,
    BaseOption,
    parameter_action,
    SubCommand,
    PassThru,
)
from cli_command_parser.testing import ParserTest


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
        fail_cases = [
            (['-im'], MissingArgument),
            (['-i', '-m'], MissingArgument),
            (['-m', '-i'], MissingArgument),
            (['-i', 'm'], NoSuchOption),
            (['-m'], MissingArgument),
            (['-i=True'], UsageError),
        ]
        self.assert_parse_fails_cases(Ipython, fail_cases)

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

    def test_combined_flags(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        success_cases = [
            (['-fb'], {'foo': True, 'bar': True}),
            (['-bf'], {'foo': True, 'bar': True}),
            (['-bff'], {'foo': True, 'bar': True}),
            (['-bfb'], {'foo': True, 'bar': True}),
            (['-bbf'], {'foo': True, 'bar': True}),
            (['-fbf'], {'foo': True, 'bar': True}),
            (['-f'], {'foo': True, 'bar': False}),
            (['-ff'], {'foo': True, 'bar': False}),
            (['-b'], {'foo': False, 'bar': True}),
            (['-bb'], {'foo': False, 'bar': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_flag_counter_combo(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Counter('-b')

        success_cases = [
            (['-fb'], {'foo': True, 'bar': 1}),
            (['-bf'], {'foo': True, 'bar': 1}),
            (['-f'], {'foo': True, 'bar': 0}),
            (['-ff'], {'foo': True, 'bar': 0}),
            (['-b'], {'foo': False, 'bar': 1}),
            (['-b3'], {'foo': False, 'bar': 3}),
            (['-bb'], {'foo': False, 'bar': 2}),
            (['-bfb'], {'foo': True, 'bar': 2}),
            (['-fbb'], {'foo': True, 'bar': 2}),
            (['-bbf'], {'foo': True, 'bar': 2}),
            (['-ffb'], {'foo': True, 'bar': 1}),
            (['-b', '-b'], {'foo': False, 'bar': 2}),
            (['-b', '-fb'], {'foo': True, 'bar': 2}),
            (['-bf', '-b'], {'foo': True, 'bar': 2}),
            (['-f', '-bb'], {'foo': True, 'bar': 2}),
            (['-fb', '-b'], {'foo': True, 'bar': 2}),
            (['-bbf'], {'foo': True, 'bar': 2}),
            (['-b', '-bf'], {'foo': True, 'bar': 2}),
            (['-bb', '-f'], {'foo': True, 'bar': 2}),
            (['-ff', '-b'], {'foo': True, 'bar': 1}),
            (['-b3', '-b'], {'foo': False, 'bar': 4}),
            (['-b', '3', '-b'], {'foo': False, 'bar': 4}),
            (['-b=3'], {'foo': False, 'bar': 3}),
            (['-b', '-b=3'], {'foo': False, 'bar': 4}),
            (['-fb', '-b=3'], {'foo': True, 'bar': 4}),
            (['-bf', '-b=3'], {'foo': True, 'bar': 4}),
            (['-b=3', '-b'], {'foo': False, 'bar': 4}),
            (['-bfb', '3'], {'foo': True, 'bar': 4}),
            (['-bf', '-b3'], {'foo': True, 'bar': 4}),
            (['-bf', '-b', '3'], {'foo': True, 'bar': 4}),
            (['-fb', '3'], {'foo': True, 'bar': 3}),
            (['-f', '-b3'], {'foo': True, 'bar': 3}),
            (['-b3', '-f'], {'foo': True, 'bar': 3}),
            (['-ffb', '3'], {'foo': True, 'bar': 3}),
            (['-ff', '-b3'], {'foo': True, 'bar': 3}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [
            (['-bf3'], NoSuchOption),
            (['-b3b'], NoSuchOption),
            (['-bb3'], NoSuchOption),
            (['-bb=3'], NoSuchOption),
            (['-bfb3'], NoSuchOption),
            (['-fb3'], NoSuchOption),
            (['-b3f'], NoSuchOption),
            (['-ffb3'], NoSuchOption),
            (['-bb', '3'], NoSuchOption),
            (['-fb', 'b'], NoSuchOption),
            (['-fb', 'f'], NoSuchOption),
            (['-fb', 'a'], NoSuchOption),
            (['-bf', '3'], NoSuchOption),
            (['-bf', 'b'], NoSuchOption),
        ]
        self.assert_parse_fails_cases(Foo, fail_cases)

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

    @skip('This case is not currently supported')  # TODO: Should this be supported?
    def test_common_positional_after_sub_command(self):
        class Foo(Command):
            sub = SubCommand()
            pos = Positional()

        class Bar(Foo):
            bar = Option('-b')

        class Baz(Foo):
            baz = Option('-b')

        bar_expected = {'pos': 'a', 'sub': 'bar', 'bar': 'c'}
        baz_expected = {'pos': 'a', 'sub': 'bar', 'baz': 'c'}
        success_cases = [
            (['bar', 'a', '-b', 'c'], bar_expected),
            (['bar', '-b', 'c', 'a'], bar_expected),
            (['-b', 'c', 'bar', 'a'], bar_expected),
            (['baz', 'a', '-b', 'c'], baz_expected),
            (['baz', '-b', 'c', 'a'], baz_expected),
            (['-b', 'c', 'baz', 'a'], baz_expected),
            (['bar', 'a'], {'pos': 'a', 'sub': 'bar', 'bar': None}),
            (['baz', 'a'], {'pos': 'a', 'sub': 'baz', 'baz': None}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        # fmt: off
        fail_cases = [
            ['a', 'bar'], ['a', 'baz'], ['baz'], ['bar'], ['a'], ['-b', 'c', 'bar'], ['-b', 'c', 'baz'], ['-b', 'c']
        ]
        # fmt: on
        self.assert_parse_fails_cases(Foo, fail_cases, UsageError)

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

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz', 'a'])

        Foo.config().ignore_unknown = True
        self.assertEqual(Foo.parse(['bar', '--baz']).ctx.remaining, ['--baz'])
        self.assertEqual(Foo.parse(['bar', '--baz', 'a']).ctx.remaining, ['--baz', 'a'])

    def test_extra_short_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        fail_cases = [['bar', '-b'], ['bar', '-b', 'a'], ['bar', '-b=a']]
        self.assert_parse_fails_cases(Foo, fail_cases, NoSuchOption)

        Foo.config().ignore_unknown = True
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

    def test_nargs_question(self):
        class CustomOption(BaseOption):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, action='store', **kwargs)
                self.nargs = Nargs('?')

            @parameter_action
            def store(self, value):
                ctx.set_parsing_value(self, value)

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

        Foo.config().ignore_unknown = True
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


class NargsTest(ParserTest):
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

    # TODO:BUG: Fix commented-out lines
    def test_single_default_with_nargs_multi(self):
        class Foo(Command):
            bar = Option('-b', nargs='+', type=int, default=1)

        success_cases = [
            # ([], {'bar': [1]}),  # Results in [] now
            (['-b', '2'], {'bar': [2]}),
            # (['-b=2', '3'], {'bar': [2, 3]}),  # Rejects 3 now
            (['--bar', '2', '3'], {'bar': [2, 3]}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
