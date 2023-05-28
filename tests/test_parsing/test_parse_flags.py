#!/usr/bin/env python

from itertools import product
from unittest import main

from cli_command_parser import Command, Option, Flag, TriFlag, Counter, AmbiguousComboMode, ParamConflict, ParamsMissing
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import NoSuchOption, UsageError, MissingArgument, AmbiguousCombo, AmbiguousShortForm
from cli_command_parser.exceptions import ParamUsageError, BadArgument
from cli_command_parser.testing import ParserTest


class ParseFlagsTest(ParserTest):
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
        class Foo(Command, ambiguous_short_combos=AmbiguousComboMode.STRICT):
            a = Flag('-a')
            b = Flag('-b')
            c = Flag('-c')
            ab = Flag('-ab')
            bc = Flag('-bc')
            abc = Flag('-abc')

        exp_error_pat = (
            'Ambiguous short form for --ab / -ab - it conflicts with: --a / -a, --b / -b\n'
            'Ambiguous short form for --abc / -abc - it conflicts with: --a / -a, --b / -b, --c / -c\n'
            'Ambiguous short form for --bc / -bc - it conflicts with: --b / -b, --c / -c'
        )
        with self.assertRaisesRegex(AmbiguousShortForm, exp_error_pat):
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

        # fmt: off
        fail_cases = [
            ['-bf3'], ['-b3b'], ['-bb3'], ['-bb=3'], ['-bfb3'], ['-fb3'], ['-b3f'], ['-ffb3'], ['-bb', '3'],
            ['-fb', 'b'], ['-fb', 'f'], ['-fb', 'a'], ['-bf', '3'], ['-bf', 'b'],
        ]
        # fmt: on
        self.assert_parse_fails_cases(Foo, fail_cases, NoSuchOption)

    def test_str_values(self):
        class Foo(Command):
            bar = Flag('-b', default='foo', const='bar')

        success_cases = [([], {'bar': 'foo'}), (['-b'], {'bar': 'bar'}), (['--bar'], {'bar': 'bar'})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_multi_char_combo(self):
        class Foo(Command, add_help=False):  # add_help=False ensures a branch is hit in command_parameters
            bar = Flag('-bar')
            baz = Flag('-ba')

        success_cases = [
            ([], {'bar': False, 'baz': False}),
            (['-bar'], {'bar': True, 'baz': False}),
            (['--bar'], {'bar': True, 'baz': False}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails(Foo, ['-baz'])

    def test_append_const_value_rejected(self):
        class Foo(Command):
            bar = Flag('-b', action='append_const')

        self.assert_parse_fails(Foo, ['-b=123'])

    # region Env Var Handling

    def test_env_var(self):
        for use_env_value in (False, True):
            with self.subTest(use_env_value=use_env_value):

                class Foo(Command):
                    bar = Flag('-b', env_var='BAR', use_env_value=use_env_value)

                t, f = {'bar': True}, {'bar': False}
                cases = [
                    ([], {}, f),
                    (['-b'], {'BAR': '0'}, t),  # cli takes precedence
                    ([], {'BAR': '0'}, f),  # env false ignored
                    ([], {'BAR': 'f'}, f),  # env false ignored
                    ([], {'BAR': '1'}, t),
                    ([], {'BAR': 'true'}, t),
                    ([], {'BAR': 'TruE'}, t),
                ]
                self.assert_env_parse_results_cases(Foo, cases)

                with self.env_vars('invalid value', BAR='foo'):
                    with self.assertRaisesRegex(ParamUsageError, 'unable to parse value=.*? from env_var='):
                        Foo.parse([])

    def test_env_vars(self):
        class Foo(Command):
            bar = Flag('-b', env_var=('FOO', 'BAR'))

        t, f = {'bar': True}, {'bar': False}
        # fmt: off
        cases = [
            ([], {}, f),
            (['-b'], {'FOO': '0'}, t),  # cli takes precedence
            (['-b'], {'BAR': '0'}, t),  # cli takes precedence
            ([], {'BAR': '0'}, f),  # env false ignored
            ([], {'FOO': 'false', 'BAR': '1'}, f),  # stops after first found env var
            ([], {'FOO': 'true', 'BAR': '0'}, t),  # stops after first found env var
            ([], {'FOO': '1'}, t),
            ([], {'BAR': '1'}, t),
            ([], {'BAR': 'true'}, t),
            ([], {'FOO': 'TruE'}, t),
            ([], {'BAR': 'TruE'}, t),
        ]
        # fmt: on
        self.assert_env_parse_results_cases(Foo, cases)

    def test_env_var_invalid_permissive(self):
        class Foo(Command):
            bar = Flag('-b', env_var='BAR', strict_env=False)

        with self.assertLogs('cli_command_parser.parser', 'WARNING'):
            self.assert_env_parse_results(Foo, [], {'BAR': 'foo'}, {'bar': False})

    def test_non_default_const_stored_from_env_var(self):
        class Foo(Command):
            bar = Flag('-b', env_var='BAR', default=True)

        t, f = {'bar': False}, {'bar': True}
        cases = [
            ([], {}, f),
            (['-b'], {'BAR': '0'}, t),  # cli takes precedence
            ([], {'BAR': '0'}, f),  # env false ignored
            ([], {'BAR': 'f'}, f),  # env false ignored
            ([], {'BAR': '1'}, t),
            ([], {'BAR': 'true'}, t),
            ([], {'BAR': 'TruE'}, t),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

    def test_non_default_const_stored_from_env_var_use_value(self):
        class Foo(Command):
            bar = Flag('-b', env_var='BAR', default=True, use_env_value=True)

        t, f = {'bar': True}, {'bar': False}
        cases = [
            ([], {}, t),
            (['-b'], {'BAR': '1'}, f),  # cli takes precedence
            ([], {'BAR': '0'}, f),  # env false ignored
            ([], {'BAR': 'f'}, f),  # env false ignored
            ([], {'BAR': '1'}, t),
            ([], {'BAR': 'true'}, t),
            ([], {'BAR': 'TruE'}, t),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

    def test_custom_env_var_type(self):
        def parse_bool(value: str) -> bool:
            if value == 'foo':
                return True
            elif value == 'bar':
                return False
            raise ValueError

        class Foo(Command):
            bar = Flag('-b', type=parse_bool, env_var='BAR')

        t, f = {'bar': True}, {'bar': False}
        cases = [
            ([], {}, f),
            (['-b'], {'BAR': '123'}, t),  # cli takes precedence
            ([], {'BAR': 'bar'}, f),
            ([], {'BAR': 'foo'}, t),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

        for val in ('1', 'true', '0', 'false'):
            with self.env_vars(f'invalid value={val}', BAR=val):
                with self.assertRaisesRegex(ParamUsageError, 'unable to parse value=.*? from env_var='):
                    Foo.parse([])

    def test_custom_env_var_const_use_value(self):
        class Foo(Command):
            bar = Flag('-b', type=str, env_var='BAR', default='foo', const='bar', use_env_value=True)

        t, f = {'bar': 'bar'}, {'bar': 'foo'}
        cases = [
            ([], {}, f),
            (['-b'], {'BAR': '123'}, t),  # cli takes precedence
            ([], {'BAR': 'bar'}, t),
            ([], {'BAR': 'foo'}, f),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

        for val in ('1', 'true', '0', 'false'):
            with self.env_vars(f'invalid value={val}', BAR=val):
                with self.assertRaisesRegex(BadArgument, 'invalid value=.*? from env_var='):
                    Foo.parse([])

    def test_env_var_append_const(self):
        class Foo(Command):
            bar = Flag('-b', env_var='BAR', action='append_const', use_env_value=True)

        cases = [
            ([], {}, {'bar': []}),
            (['-b'], {'BAR': '0'}, {'bar': [True]}),  # cli takes precedence
            ([], {'BAR': '1'}, {'bar': [True]}),
            ([], {'BAR': '0'}, {'bar': [False]}),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

    # endregion


class ParseTriFlagsTest(ParserTest):
    def test_alt_opt_mutual_exclusivity(self):
        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B')

        t, f = {'bar': True}, {'bar': False}
        success_cases = [([], {'bar': None}), (['--bar'], t), (['-b'], t), (['--no-bar'], f), (['-B'], f)]
        self.assert_parse_results_cases(Foo, success_cases)

        pos, neg = ('--bar', '-b'), ('--no-bar', '-B')
        fail_cases = [['-bB'], ['-Bb'], *(list(t) for g in ((pos, neg), (neg, pos)) for t in product(*g))]
        self.assert_parse_fails_cases(Foo, fail_cases, ParamConflict)

    def test_required_tri_flag(self):
        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B', required=True)

        t, f = {'bar': True}, {'bar': False}
        success_cases = [(['--bar'], t), (['-b'], t), (['--no-bar'], f), (['-B'], f)]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails(Foo, [], ParamsMissing)
        pos, neg = ('--bar', '-b'), ('--no-bar', '-B')
        fail_cases = [['-bB'], ['-Bb'], *(list(t) for g in ((pos, neg), (neg, pos)) for t in product(*g))]
        self.assert_parse_fails_cases(Foo, fail_cases, ParamConflict)

    def test_repeated_same_value_ignored(self):
        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B')

        t, f = {'bar': True}, {'bar': False}
        # fmt: off
        success_cases = [
            (['--bar', '--bar'], t), (['-b', '--bar'], t), (['--bar', '-b'], t), (['-b', '-b'], t),
            (['--no-bar', '--no-bar'], f), (['-B', '--no-bar'], f), (['--no-bar', '-B'], f), (['-B', '-B'], f),
        ]
        # fmt: on
        self.assert_parse_results_cases(Foo, success_cases)

    # region Env Var Handling

    def test_env_var(self):
        for use_env_value in (False, True):
            with self.subTest(use_env_value=use_env_value):

                class Foo(Command):
                    bar = TriFlag('-b', alt_short='-B', env_var='BAR', use_env_value=use_env_value)

                d, t, f = {'bar': None}, {'bar': True}, {'bar': False}
                cases = [
                    ([], {}, d),
                    (['-b'], {'BAR': '0'}, t),  # cli takes precedence
                    ([], {'BAR': '0'}, f),
                    ([], {'BAR': 'f'}, f),
                    ([], {'BAR': '1'}, t),
                    ([], {'BAR': 'true'}, t),
                    ([], {'BAR': 'TruE'}, t),
                ]
                self.assert_env_parse_results_cases(Foo, cases)

                with self.env_vars('invalid value', BAR='foo'):
                    with self.assertRaisesRegex(ParamUsageError, 'unable to parse value=.*? from env_var='):
                        Foo.parse([])

    def test_env_var_use_value_default(self):
        parse_func = {'foo': True, 'bar': False, 'baz': None, 'abc': '123'}.__getitem__

        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B', env_var='BAR', use_env_value=True, type=parse_func)

        d, t, f = {'bar': None}, {'bar': True}, {'bar': False}
        cases = [
            ([], {}, d),
            (['-b'], {'BAR': '0'}, t),  # cli takes precedence
            ([], {'BAR': 'foo'}, t),
            ([], {'BAR': 'bar'}, f),
            ([], {'BAR': 'baz'}, d),
        ]
        self.assert_env_parse_results_cases(Foo, cases)

        for val in ('1', 'true', '0', 'false'):
            with self.env_vars(f'invalid value={val}', BAR=val):
                with self.assertRaisesRegex(ParamUsageError, 'unable to parse value=.*? from env_var='):
                    Foo.parse([])

        with self.env_vars(f'invalid value={val}', BAR='abc'):
            with self.assertRaisesRegex(BadArgument, 'invalid value=.*? from env_var='):
                Foo.parse([])

    # endregion


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
