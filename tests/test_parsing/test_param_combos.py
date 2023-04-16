#!/usr/bin/env python

from abc import ABC
from unittest import main

from cli_command_parser.commands import Command
from cli_command_parser.config import AmbiguousComboMode
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import NoSuchOption, ParamsMissing, UsageError, MissingArgument, ParamUsageError
from cli_command_parser.exceptions import AmbiguousCombo, AmbiguousShortForm, CommandDefinitionError
from cli_command_parser.parameters import Positional, Option, Flag, Counter, SubCommand
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

    def test_ambiguous_combo_message(self):
        class Foo(Command):
            a = Flag('-a')
            b = Flag('-b')
            c = Flag('-c')
            ab = Flag('-ab')
            de = Flag('-de')

        exp_pat = "part of argument='-abc' may match multiple parameters: --a / -a, --ab / -ab, --b / -b"
        with self.assertRaisesRegex(AmbiguousCombo, exp_pat):
            Foo.parse(['-abc'])

    def test_combined_flags_ambiguous(self):
        exact_match_cases = [
            (['-abc'], {'a': False, 'b': False, 'c': False, 'ab': False, 'bc': False, 'abc': True}),
        ]
        always_success_cases = [
            ([], {'a': False, 'b': False, 'c': False, 'ab': False, 'bc': False, 'abc': False}),
            (['-a'], {'a': True, 'b': False, 'c': False, 'ab': False, 'bc': False, 'abc': False}),
            (['-ab'], {'a': False, 'b': False, 'c': False, 'ab': True, 'bc': False, 'abc': False}),
            (['-ba'], {'a': True, 'b': True, 'c': False, 'ab': False, 'bc': False, 'abc': False}),
            (['-bc'], {'a': False, 'b': False, 'c': False, 'ab': False, 'bc': True, 'abc': False}),
            (['-cb'], {'a': False, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-ac'], {'a': True, 'b': False, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-ca'], {'a': True, 'b': False, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
        ]
        ambiguous_success_cases = [
            (['-cab'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-abcc'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-bbc'], {'a': False, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-bcc'], {'a': False, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-aab'], {'a': True, 'b': True, 'c': False, 'ab': False, 'bc': False, 'abc': False}),
            (['-abbc'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-bcab'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-bcaab'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
            (['-abcabc'], {'a': True, 'b': True, 'c': True, 'ab': False, 'bc': False, 'abc': False}),
        ]
        ambiguous_fail_cases = [(args, AmbiguousCombo) for args, _ in ambiguous_success_cases]

        cases = [
            (AmbiguousComboMode.IGNORE, always_success_cases + exact_match_cases + ambiguous_success_cases, []),
            (AmbiguousComboMode.PERMISSIVE, always_success_cases + exact_match_cases, ambiguous_fail_cases),
        ]
        for mode, success_cases, fail_cases in cases:
            with self.subTest(ambiguous_short_combos=mode):

                class Foo(Command, ambiguous_short_combos=mode):
                    a = Flag('-a')
                    b = Flag('-b')
                    c = Flag('-c')
                    ab = Flag('-ab')
                    bc = Flag('-bc')
                    abc = Flag('-abc')

                self.assert_parse_results_cases(Foo, success_cases)
                self.assert_parse_fails_cases(Foo, fail_cases)

    def test_combined_flags_ambiguous_strict_rejected(self):
        exp_error_pat = (
            'Ambiguous short form for --ab / -ab - it conflicts with: --a / -a, --b / -b\n'
            'Ambiguous short form for --abc / -abc - it conflicts with: --a / -a, --b / -b, --c / -c\n'
            'Ambiguous short form for --bc / -bc - it conflicts with: --b / -b, --c / -c'
        )
        with self.assertRaisesRegex(AmbiguousShortForm, exp_error_pat):

            class Foo(Command, ambiguous_short_combos=AmbiguousComboMode.STRICT):
                a = Flag('-a')
                b = Flag('-b')
                c = Flag('-c')
                ab = Flag('-ab')
                bc = Flag('-bc')
                abc = Flag('-abc')

            get_params(Foo)

    def test_combined_flags_ambiguous_strict_parsing(self):
        class Foo(Command, ambiguous_short_combos=AmbiguousComboMode.STRICT):
            a = Flag('-a')
            b = Flag('-b')
            c = Flag('-c')

        success_cases = [
            ([], {'a': False, 'b': False, 'c': False}),
            (['-ab'], {'a': True, 'b': True, 'c': False}),
            (['-ba'], {'a': True, 'b': True, 'c': False}),
            (['-bc'], {'a': False, 'b': True, 'c': True}),
            (['-cb'], {'a': False, 'b': True, 'c': True}),
            (['-ac'], {'a': True, 'b': False, 'c': True}),
            (['-ca'], {'a': True, 'b': False, 'c': True}),
            (['-cab'], {'a': True, 'b': True, 'c': True}),
            (['-abcc'], {'a': True, 'b': True, 'c': True}),
            (['-bbc'], {'a': False, 'b': True, 'c': True}),
            (['-bcc'], {'a': False, 'b': True, 'c': True}),
            (['-aab'], {'a': True, 'b': True, 'c': False}),
            (['-abbc'], {'a': True, 'b': True, 'c': True}),
            (['-bcab'], {'a': True, 'b': True, 'c': True}),
            (['-bcaab'], {'a': True, 'b': True, 'c': True}),
            (['-abcabc'], {'a': True, 'b': True, 'c': True}),
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


class PositionalAfterSubcommandTest(ParserTest):
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
