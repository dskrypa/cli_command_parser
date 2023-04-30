#!/usr/bin/env python

import re
from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, Flag, Option, TriFlag, ParamGroup
from cli_command_parser.exceptions import UsageError, ParameterDefinitionError
from cli_command_parser.exceptions import ParamUsageError, MissingArgument, BadArgument, ParamsMissing, ParamConflict
from cli_command_parser.nargs import REMAINDER
from cli_command_parser.testing import ParserTest, get_help_text, get_usage_text

STANDALONE_DASH_B = re.compile(r'(?<!-)-b\b')


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
            ({'nargs': 0}, ParameterDefinitionError),
            ({'nargs': (0, 2)}, ParameterDefinitionError),
            ({'nargs': range(2)}, ParameterDefinitionError),
        ]
        for val in ('?', '*', 'REMAINDER'):
            fail_cases += [
                ({'nargs': val}, ParameterDefinitionError, 'use Flag or Counter for Options with 0 args'),
                ({'nargs': val, 'required': True}, ParameterDefinitionError),
                ({'nargs': val, 'required': False}, ParameterDefinitionError),
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

    # region Name Mode

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

    def test_name_none_missing_options(self):
        class Foo(Command, option_name_mode=None):
            bar = Option()

        with self.assertRaisesRegex(ParameterDefinitionError, 'No option strings were registered'):
            Foo().parse([])

    def test_name_none(self):
        class Foo(Command, option_name_mode='NONE'):
            bar = Option('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--bar', help_text)
        self.assertNotIn('--bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B)

        success_cases = [([], {'bar': None}), (['-b', 'foo'], {'bar': 'foo'})]
        self.assert_parse_results_cases(Foo, success_cases)

        fail_cases = [['--bar'], ['-b'], ['--bar', 'foo']]
        self.assert_argv_parse_fails_cases(Foo, fail_cases)

    # endregion

    def test_option_strs_repr(self):
        class Foo(Command, option_name_mode='-'):
            a_b = Flag()
            a_c = TriFlag()

        self.assertEqual('<OptionStrings[name_mode=OptionNameMode.DASH][--a-b]>', repr(Foo.a_b.option_strs))
        expected = '<TriFlagOptionStrings[name_mode=OptionNameMode.DASH][--a-c, --no-a-c]>'
        self.assertEqual(expected, repr(Foo.a_c.option_strs))

    def test_type_annotation_with_remainder_ignored(self):
        class Foo(Command):
            bar: int = Option(nargs=(1, REMAINDER))

        self.assertIsNone(Foo.bar.type)  # noqa

    def test_type_with_remainder_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Type casting and choices are not supported'):

            class Foo(Command):
                bar = Option(nargs=(1, REMAINDER), type=int)

    def test_choices_with_remainder_rejected(self):
        with self.assertRaisesRegex(ParameterDefinitionError, 'Type casting and choices are not supported'):

            class Foo(Command):
                bar = Option(nargs=(1, REMAINDER), choices=('a', 'b'))

    def test_bad_leading_dash_with_remainder_rejected(self):
        expected = 'only allow_leading_dash=AllowLeadingDash.ALWAYS'
        for allow_leading_dash in ('numeric', False):
            with self.subTest(allow_leading_dash=allow_leading_dash):
                with self.assertRaisesRegex(ParameterDefinitionError, expected):

                    class Foo(Command):
                        bar = Option(nargs=(1, REMAINDER), allow_leading_dash=allow_leading_dash)


class EnvVarTest(ParserTest):
    def test_no_env_vars(self):
        self.assertEqual([], list(Option().env_vars()))

    def test_env_var(self):
        class Foo(Command):
            bar: int = Option('-b', default=123, env_var='TEST_VAR_123')

        # fmt: off
        cases = [
            ([], {}, {'bar': 123}),                                     # param default
            (['-b', '987'], {'TEST_VAR_123': '234'}, {'bar': 987}),     # cli override
            ([], {'TEST_VAR_123': '234'}, {'bar': 234}),                # env override
        ]
        # fmt: on
        self.assert_env_parse_results_cases(Foo, cases)

    def test_env_vars(self):
        class Foo(Command):
            bar: int = Option('-b', default=123, env_var=('TEST_VAR_123', 'TEST_VAR_234'))

        # fmt: off
        cases = [
            ([], {}, {'bar': 123}),                                                 # param default
            (['-b', '987'], {'TEST_VAR_123': '234'}, {'bar': 987}),                 # cli override
            ([], {'TEST_VAR_123': '234', 'TEST_VAR_234': '345'}, {'bar': 234}),     # env override 1
            ([], {'TEST_VAR_234': '345'}, {'bar': 345}),                            # env override 2
        ]
        # fmt: on
        self.assert_env_parse_results_cases(Foo, cases)

    def test_env_var_required(self):
        class Foo(Command):
            bar: int = Option('-b', env_var='TEST_VAR_123', required=True)

        with self.env_vars('no value'), self.assertRaises(ParamsMissing):
            Foo.parse([])

        # fmt: off
        cases = [
            (['-b', '987'], {'TEST_VAR_123': '234'}, {'bar': 987}),     # cli override
            ([], {'TEST_VAR_123': '234'}, {'bar': 234}),                # env override
        ]
        # fmt: on
        self.assert_env_parse_results_cases(Foo, cases)

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

        cases = [
            ([], {'FOO': 'a'}, {'foo': 'a', 'bar': None}),  # env ok 1
            ([], {'BAR': 'b'}, {'foo': None, 'bar': 'b'}),  # env ok 2
            (['-f', 'a'], {}, {'foo': 'a', 'bar': None}),  # cli ok 1
            (['-b', 'b'], {}, {'foo': None, 'bar': 'b'}),  # cli ok 2
        ]
        self.assert_env_parse_results_cases(Cmd, cases)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
