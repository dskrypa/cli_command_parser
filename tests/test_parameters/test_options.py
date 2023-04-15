#!/usr/bin/env python

import re
from contextlib import contextmanager
from unittest import main
from unittest.mock import Mock, patch

from cli_command_parser import Command, Counter, Flag, Option, TriFlag, ParamGroup
from cli_command_parser.exceptions import NoSuchOption, UsageError, ParameterDefinitionError, CommandDefinitionError
from cli_command_parser.exceptions import ParamUsageError, MissingArgument, BadArgument, ParamsMissing, ParamConflict
from cli_command_parser.testing import ParserTest, get_help_text, get_usage_text

STANDALONE_DASH_B = re.compile(r'(?<!-)-b\b')
OPT_ENV_MOD = 'cli_command_parser.parser.environ'


class OptionTest(ParserTest):
    def test_choice_ok(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertEqual(Foo.parse(['-f', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['-f', 'b']).foo, 'b')
        self.assertEqual(Foo.parse(['--foo', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['--foo', 'b']).foo, 'b')

    def test_choice_bad(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        with self.assertRaises(UsageError):
            Foo.parse(['-f', 'c'])

    def test_instance_values(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        a = Foo.parse(['-f', 'a'])
        b = Foo.parse(['-f', 'b'])
        self.assertEqual(a.foo, 'a')
        self.assertEqual(b.foo, 'b')

    def test_value_missing(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Option('-b')

        cases = (
            ['--foo', '--bar'],
            ['--foo', '-b'],
            ['--bar', '--foo'],
            ['-b', '--foo'],
            ['-f', '--bar'],
            ['-f', '-b'],
            ['--bar', '-f'],
            ['-b', '-f'],
            ['-b'],
            ['--bar'],
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(MissingArgument):
                Foo.parse(case)

        self.assertTrue(Foo.parse(['--foo']).foo)

    def test_invalid_value(self):
        class Foo(Command):
            bar = Option(type=Mock(side_effect=TypeError))

        with self.assertRaises(BadArgument):
            Foo.parse(['--bar', '1'])

    def test_nargs_0_rejected(self):
        fail_cases = [
            ({'nargs': '?'}, ParameterDefinitionError, 'use Flag or Counter for Options with 0 args'),
            ({'nargs': '?', 'required': True}, ParameterDefinitionError),
            ({'nargs': '?', 'required': False}, ParameterDefinitionError),
            ({'nargs': '*'}, ParameterDefinitionError, 'use Flag or Counter for Options with 0 args'),
            ({'nargs': '*', 'required': True}, ParameterDefinitionError),
            ({'nargs': '*', 'required': False}, ParameterDefinitionError),
            ({'nargs': 0}, ParameterDefinitionError),
            ({'nargs': (0, 2)}, ParameterDefinitionError),
            ({'nargs': range(2)}, ParameterDefinitionError),
        ]
        self.assert_call_fails_cases(Option, fail_cases)

    def test_nargs_0_range_tip_step_1(self):
        expected = r'try using range\(1, 2\) instead, or use Flag or Counter for Options with 0 args'
        with self.assertRaisesRegex(ParameterDefinitionError, expected):

            class Foo(Command):
                bar = Option(nargs=range(2))

    def test_nargs_0_range_tip_step_2_matches_stop(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'use Flag or Counter for Options with 0 args'):

            class Foo(Command):
                bar = Option(nargs=range(0, 2, 2))

    def test_nargs_0_range_tip_step_2(self):
        expected = r'try using range\(2, 3, 2\) instead, or use Flag or Counter for Options with 0 args'
        with self.assertRaisesRegex(ParameterDefinitionError, expected):

            class Foo(Command):
                bar = Option(nargs=range(0, 3, 2))

    def test_bad_option_strs_rejected(self):
        # fmt: off
        fail_cases = [
            '---foo', '-f-', '-foo--', '--foo-', '--foo=', '-f=', '-foo=', '=', '-', '--', '---', '-=', '--=', '-a-a'
        ]
        # fmt: on
        for option_str in fail_cases:
            with self.subTest(option_str=option_str), self.assertRaises(ParameterDefinitionError):
                Option(option_str)

    def test_re_assign_rejected(self):
        class Foo(Command):
            bar = Option('-b')

        self.assert_parse_fails(Foo, ['-b', 'a', '-b', 'b'], ParamUsageError)

    def test_too_many_rejected(self):
        class Foo(Command):
            bar = Option('-b', nargs=2)

        self.assert_parse_results(Foo, ['-b', 'a', 'b'], {'bar': ['a', 'b']})
        self.assert_parse_fails(Foo, ['-b', 'a', 'b', '-b', 'b'], ParamUsageError)

    def test_explicit_long_opt(self):
        class Foo(Command):
            foo = Option('--bar', '-b')

        self.assertNotIn('--foo', Foo.foo.option_strs.long)

    def test_action_nargs_mismatch_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Option(nargs=2, action='store')

        self.assertEqual(1, Option(action='store').nargs)

    def test_usage(self):
        self.assertEqual('--foo', Option('--foo').format_usage())
        self.assertEqual('[--foo bar]', Option('--foo', metavar='bar', required=False).formatter.format_basic_usage())
        self.assertEqual('--foo bar', Option('--foo', metavar='bar', required=True).formatter.format_basic_usage())

    def test_not_required_nargs_plus_default(self):
        class Foo(Command):
            bar = Option('-b', nargs='+')

        foo = Foo.parse_and_run([])
        self.assertFalse(foo.bar)
        self.assertEqual([], foo.bar)

    def test_required_default_rejected(self):
        cases = (None, 1, 'test')
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ParameterDefinitionError):
                Option(required=True, default=case)

    def test_name_both(self):
        class Foo(Command, option_name_mode='*'):
            foo_bar = Option('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertIn('--foo_bar', help_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': 'baz'}
        success_cases = [(['--foo-bar', 'baz'], exp), (['--foo_bar', 'baz'], exp), (['-b', 'baz'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_underscore(self):
        class Foo(Command, option_name_mode='*_'):
            foo_bar = Option('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo-bar', help_text)
        self.assertNotIn('--foo-bar', usage_text)
        self.assertIn('--foo_bar', help_text)
        self.assertIn('--foo_bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': 'baz'}
        success_cases = [(['--foo-bar', 'baz'], exp), (['--foo_bar', 'baz'], exp), (['-b', 'baz'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_dash(self):
        class Foo(Command, option_name_mode='*-'):
            foo_bar = Option('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo_bar', help_text)
        self.assertNotIn('--foo_bar', usage_text)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': 'baz'}
        success_cases = [(['--foo-bar', 'baz'], exp), (['--foo_bar', 'baz'], exp), (['-b', 'baz'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_option_strs_repr(self):
        class Foo(Command, option_name_mode='-'):
            a_b = Flag()
            a_c = TriFlag()

        self.assertEqual('<OptionStrings[name_mode=OptionNameMode.DASH][--a-b]>', repr(Foo.a_b.option_strs))
        expected = '<TriFlagOptionStrings[name_mode=OptionNameMode.DASH][--a-c, --no-a-c]>'
        self.assertEqual(expected, repr(Foo.a_c.option_strs))


class EnvVarTest(ParserTest):
    @contextmanager
    def env_vars(self, case: str, **env_vars):
        with self.subTest(case=case), patch(OPT_ENV_MOD, env_vars):
            yield

    def test_env_var(self):
        class Foo(Command):
            bar: int = Option('-b', default=123, env_var='TEST_VAR_123')

        with self.env_vars('param default'):
            self.assertEqual(123, Foo.parse([]).bar)
        with self.env_vars('cli override', TEST_VAR_123='234'):
            self.assertEqual(987, Foo.parse(['-b', '987']).bar)
        with self.env_vars('env override', TEST_VAR_123='234'):
            self.assertEqual(234, Foo.parse([]).bar)

    def test_env_vars(self):
        class Foo(Command):
            bar: int = Option('-b', default=123, env_var=('TEST_VAR_123', 'TEST_VAR_234'))

        with self.env_vars('param default'):
            self.assertEqual(123, Foo.parse([]).bar)
        with self.env_vars('cli override', TEST_VAR_123='234'):
            self.assertEqual(987, Foo.parse(['-b', '987']).bar)
        with self.env_vars('env override 1', TEST_VAR_123='234', TEST_VAR_234='345'):
            self.assertEqual(234, Foo.parse([]).bar)
        with self.env_vars('env override 2', TEST_VAR_234='345'):
            self.assertEqual(345, Foo.parse([]).bar)

    def test_env_var_required(self):
        class Foo(Command):
            bar: int = Option('-b', env_var='TEST_VAR_123', required=True)

        with self.env_vars('no value'), self.assertRaises(ParamsMissing):
            Foo.parse([])
        with self.env_vars('cli override', TEST_VAR_123='234'):
            self.assertEqual(987, Foo.parse(['-b', '987']).bar)
        with self.env_vars('env override', TEST_VAR_123='234'):
            self.assertEqual(234, Foo.parse([]).bar)

    def test_env_var_in_required_group(self):
        class Cmd(Command):
            with ParamGroup(mutually_exclusive=True, required=True):
                foo = Option('-f', env_var='FOO')
                bar = Option('-b', env_var='BAR')

        with self.env_vars('no value'), self.assertRaises(ParamsMissing):
            Cmd.parse([])
        with self.env_vars('both env vars', FOO='a', BAR='b'), self.assertRaises(ParamConflict):
            Cmd.parse([])
        with self.env_vars('combo 1', FOO='a'), self.assertRaises(ParamConflict):
            Cmd.parse(['-b', 'b'])
        with self.env_vars('combo 2', BAR='b'), self.assertRaises(ParamConflict):
            Cmd.parse(['-f', 'a'])
        with self.env_vars('env ok 1', FOO='a'):
            self.assertEqual('a', Cmd.parse([]).foo)
        with self.env_vars('env ok 2', BAR='b'):
            self.assertEqual('b', Cmd.parse([]).bar)
        with self.env_vars('cli ok 1'):
            self.assertEqual('a', Cmd.parse(['-f', 'a']).foo)
        with self.env_vars('cli ok 2'):
            self.assertEqual('b', Cmd.parse(['-b', 'b']).bar)


class FlagTest(ParserTest):
    def test_default_consts(self):
        cases = [(True, False), (False, True)]
        for default, expected in cases:
            with self.subTest(default=default, expected=expected):
                self.assertEqual(expected, Flag(default=default).const)

        self.assert_call_fails(
            Flag, {'default': 42}, ParameterDefinitionError, "Missing parameter='const' for Flag with default=42"
        )

    def test_default_defaults(self):
        cases = [(True, False), (False, True), (42, None)]
        for const, expected in cases:
            with self.subTest(const=const, expected=expected):
                self.assertEqual(expected, Flag(const=const).default)

    def test_annotation_ignored(self):
        for annotation in (bool, int, str, None):
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Flag()

                self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': True}), ([], {'bar': False})])

    def test_store_false(self):
        class Foo(Command):
            bar = Flag(default=True)

        self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': False}), ([], {'bar': True})])

    def test_store_const(self):
        class Foo(Command):
            bar = Flag('-b', const=42)

        self.assert_parse_results_cases(Foo, [(['--bar'], {'bar': 42}), ([], {'bar': None}), (['-bb'], {'bar': 42})])

    def test_append_default(self):
        class Foo(Command):
            bar = Flag('-b', action='append_const')

        success_cases = [(['--bar'], {'bar': [True]}), ([], {'bar': []}), (['-bb'], {'bar': [True, True]})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_append_const(self):
        class Foo(Command):
            bar = Flag('-b', const=42, action='append_const')

        success_cases = [(['--bar'], {'bar': [42]}), ([], {'bar': []}), (['-bb'], {'bar': [42, 42]})]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(type=int)

    def test_metavar_not_allowed(self):
        with self.assertRaisesRegex(TypeError, 'got an unexpected keyword argument:'):
            Flag(metavar='foo')

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(choices=(1, 2))

    def test_allow_leading_dash_not_allowed(self):
        with self.assertRaises(TypeError):
            Flag(allow_leading_dash=True)

    def test_name_both(self):
        class Foo(Command, option_name_mode='*'):
            foo_bar = Flag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertIn('--foo_bar', help_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': True}
        success_cases = [(['--foo-bar'], exp), (['--foo_bar'], exp), (['-b'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_underscore(self):
        class Foo(Command, option_name_mode='*_'):
            foo_bar = Flag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo-bar', help_text)
        self.assertNotIn('--foo-bar', usage_text)
        self.assertIn('--foo_bar', help_text)
        self.assertIn('--foo_bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': True}
        success_cases = [(['--foo-bar'], exp), (['--foo_bar'], exp), (['-b'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_dash(self):
        class Foo(Command, option_name_mode='*-'):
            foo_bar = Flag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo_bar', help_text)
        self.assertNotIn('--foo_bar', usage_text)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp = {'foo_bar': True}
        success_cases = [(['--foo-bar'], exp), (['--foo_bar'], exp), (['-b'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)


class TriFlagTest(ParserTest):
    def test_trinary(self):
        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B', name_mode='-')
            baz = Flag('-Z')

        success_cases = [
            ([], {'bar': None, 'baz': False}),
            (['-b'], {'bar': True, 'baz': False}),
            (['--bar'], {'bar': True, 'baz': False}),
            (['-B'], {'bar': False, 'baz': False}),
            (['--no-bar'], {'bar': False, 'baz': False}),
            (['-bZ'], {'bar': True, 'baz': True}),
            (['-BZ'], {'bar': False, 'baz': True}),
            (['-Zb'], {'bar': True, 'baz': True}),
            (['-ZB'], {'bar': False, 'baz': True}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            TriFlag(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            TriFlag(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            TriFlag(choices=(1, 2))

    def test_metavar_not_allowed(self):
        with self.assertRaises(TypeError):
            TriFlag(metavar='foo')

    def test_allow_leading_dash_not_allowed(self):
        with self.assertRaises(TypeError):
            TriFlag(allow_leading_dash=True)

    def test_bad_consts(self):
        exc = ParameterDefinitionError
        fail_cases = [({'consts': None}, exc), ({'consts': (1,)}, exc), ({'consts': [1, 2, 3]}, exc)]
        self.assert_call_fails_cases(TriFlag, fail_cases)

    def test_bad_alt_short(self):
        with self.assertRaises(ParameterDefinitionError):
            TriFlag(alt_short='-a-a')

    def test_bad_alt_prefix(self):
        exc = ParameterDefinitionError
        fail_cases = [({'alt_prefix': '-no'}, exc), ({'alt_prefix': 'a=b'}, exc), ({'alt_prefix': '='}, exc)]
        self.assert_call_fails_cases(TriFlag, fail_cases)

    def test_bad_combos(self):
        cases = [{'alt_short': '-B'}, {'alt_long': '--baz'}, {'alt_long': '--baz', 'alt_short': '-B'}]
        for case in cases:
            with self.subTest(case=case):

                class Foo(Command):
                    bar = TriFlag('-b', **case)
                    baz = Flag('-B')

                with self.assertRaises(CommandDefinitionError):
                    Foo.parse([])

    def test_no_alt_short(self):
        class Foo(Command):
            spam = TriFlag('-s', name_mode='-')

        self.assertSetEqual({'--no-spam'}, Foo.spam.option_strs.alt_allowed)

    def test_name_both(self):
        class Foo(Command, option_name_mode='*'):
            foo_bar = TriFlag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertIn('--no-foo-bar', help_text)
        self.assertIn('--no-foo-bar', usage_text)

        self.assertIn('--foo_bar', help_text)
        self.assertIn('--no_foo_bar', help_text)

        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp, alt = {'foo_bar': True}, {'foo_bar': False}
        success_cases = [
            ([], {'foo_bar': None}),
            (['--foo-bar'], exp),
            (['--foo_bar'], exp),
            (['--no-foo-bar'], alt),
            (['--no_foo_bar'], alt),
            (['-b'], exp),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_underscore(self):
        class Foo(Command, option_name_mode='*_'):
            foo_bar = TriFlag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo-bar', help_text)
        self.assertNotIn('--foo-bar', usage_text)
        self.assertNotIn('--no-foo-bar', help_text)
        self.assertNotIn('--no-foo-bar', usage_text)

        self.assertIn('--foo_bar', help_text)
        self.assertIn('--foo_bar', usage_text)
        self.assertIn('--no_foo_bar', help_text)
        self.assertIn('--no_foo_bar', usage_text)

        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp, alt = {'foo_bar': True}, {'foo_bar': False}
        success_cases = [
            ([], {'foo_bar': None}),
            (['--foo-bar'], exp),
            (['--foo_bar'], exp),
            (['--no-foo-bar'], alt),
            (['--no_foo_bar'], alt),
            (['-b'], exp),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_both_dash(self):
        class Foo(Command, option_name_mode='*-'):
            foo_bar = TriFlag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--foo_bar', help_text)
        self.assertNotIn('--foo_bar', usage_text)
        self.assertNotIn('--no_foo_bar', help_text)
        self.assertNotIn('--no_foo_bar', usage_text)

        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertIn('--no-foo-bar', help_text)
        self.assertIn('--no-foo-bar', usage_text)

        self.assertRegex(help_text, STANDALONE_DASH_B)
        exp, alt = {'foo_bar': True}, {'foo_bar': False}
        success_cases = [
            ([], {'foo_bar': None}),
            (['--foo-bar'], exp),
            (['--foo_bar'], exp),
            (['--no-foo-bar'], alt),
            (['--no_foo_bar'], alt),
            (['-b'], exp),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_auto_long_with_alt(self):
        cases = [({}, '--no-abc'), ({'option_name_mode': '_'}, '--no_abc')]
        for kwargs, abc_long in cases:
            with self.subTest(kwargs=kwargs, abc_long=abc_long):

                class Foo(Command, **kwargs):
                    foo = TriFlag(alt_long='--no-foo')
                    bar = TriFlag('--bar', alt_long='--baz')
                    abc = TriFlag()

                self.assertEqual(['--no-foo', '--foo'], Foo.foo.option_strs.long)
                self.assertEqual(['--bar', '--baz'], Foo.bar.option_strs.long)
                self.assertEqual([abc_long, '--abc'], Foo.abc.option_strs.long)


class CounterTest(ParserTest):
    def test_counter_default(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse([]).verbose, 0)

    def test_counter_1(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse(['-v']).verbose, 1)
        self.assertEqual(Foo.parse(['--verbose']).verbose, 1)
        with self.assertRaises(NoSuchOption):
            Foo.parse(['-verbose'])

    def test_counter_multi(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-{}'.format('v' * n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose'] * n).verbose, n)

    def test_counter_num_no_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v{n}']).verbose, n)

    def test_counter_num_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-v', str(n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose', str(n)]).verbose, n)

    def test_counter_num_eq(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v={n}']).verbose, n)
                self.assertEqual(Foo.parse([f'--verbose={n}']).verbose, n)

    def test_combined_counters(self):
        class Foo(Command):
            foo = Counter('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (2, 2),
            '-fbfb': (2, 2),
            '-ffb': (2, 1),
            '-fbf': (2, 1),
            '-fbb': (1, 2),
            '-bfb': (1, 2),
            '-bb': (0, 2),
            '-ff': (2, 0),
            ('-fb', '3'): (1, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_counter_flag_combo(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (True, 2),
            '-fbfb': (True, 2),
            '-ffb': (True, 1),
            '-fbf': (True, 1),
            '-fbb': (True, 2),
            '-bfb': (True, 2),
            '-bb': (False, 2),
            '-ff': (True, 0),
            ('-fb', '3'): (True, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_bad_default(self):
        with self.assertRaises(ParameterDefinitionError):
            Counter(default=1.5)  # noqa

    def test_prepare_value(self):
        self.assertEqual(1, Counter().prepare_value(None))

    def test_validate(self):
        self.assertTrue(Counter().is_valid_arg('1'))
        self.assertFalse(Counter().is_valid_arg('1.5'))

    def test_nargs_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(nargs='+')

    def test_type_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(type=int)

    def test_choices_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(choices=(1, 2))

    def test_allow_leading_dash_not_allowed(self):
        with self.assertRaises(TypeError):
            Counter(allow_leading_dash=True)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
