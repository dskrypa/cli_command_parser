#!/usr/bin/env python

import re
from unittest import main

from cli_command_parser import Command, Flag, TriFlag
from cli_command_parser.exceptions import ParameterDefinitionError, CommandDefinitionError
from cli_command_parser.testing import ParserTest, get_help_text, get_usage_text

STANDALONE_DASH_B_LC = re.compile(r'(?<!-)-b\b')
STANDALONE_DASH_B_UC = re.compile(r'(?<!-)-B\b')


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

    # region Test Param Actions

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

    # endregion

    # region Unsupported Kwargs

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

    # endregion

    # region Name Mode

    def test_name_both(self):
        class Foo(Command, option_name_mode='*'):
            foo_bar = Flag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo-bar', usage_text)
        self.assertIn('--foo_bar', help_text)
        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
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
        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
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
        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
        exp = {'foo_bar': True}
        success_cases = [(['--foo-bar'], exp), (['--foo_bar'], exp), (['-b'], exp)]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_name_none_missing_options(self):
        class Foo(Command, option_name_mode=None):
            bar = Flag()

        with self.assertRaisesRegex(ParameterDefinitionError, 'No option strings were registered'):
            Foo().parse([])

    def test_name_none(self):
        class Foo(Command, option_name_mode='NONE'):
            bar = Flag('-b')

        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertNotIn('--bar', help_text)
        self.assertNotIn('--bar', usage_text)
        self.assertRegex(help_text, STANDALONE_DASH_B_LC)

        success_cases = [([], {'bar': False}), (['-b'], {'bar': True})]
        self.assert_parse_results_cases(Foo, success_cases)
        self.assert_parse_fails(Foo, ['--bar'])

    # endregion


class TriFlagTest(ParserTest):
    def test_trinary(self):
        class Foo(Command):
            bar = TriFlag('-b', alt_short='-B')
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

    # region Unsupported Kwargs

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

    # endregion

    def test_bad_consts(self):
        exc = ParameterDefinitionError
        fail_cases = [({'consts': None}, exc), ({'consts': (1,)}, exc), ({'consts': [1, 2, 3]}, exc)]
        self.assert_call_fails_cases(TriFlag, fail_cases)

    def test_default_in_consts_rejected(self):
        cases = [((None, 'foo'), None), (('foo', None), None), ((True, False), True), ((True, False), False)]
        for consts, default in cases:
            with self.subTest(consts=consts, default=default):
                with self.assertRaisesRegex(ParameterDefinitionError, 'the default must not match either value'):
                    TriFlag(consts=consts, default=default)

    # region Option Strings

    def test_bad_alt_short(self):
        with self.assertRaises(ParameterDefinitionError):
            TriFlag(alt_short='-a-a')

    def test_bad_alt_prefix(self):
        exc = ParameterDefinitionError
        fail_cases = [({'alt_prefix': '-no'}, exc), ({'alt_prefix': 'a=b'}, exc), ({'alt_prefix': '='}, exc)]
        self.assert_call_fails_cases(TriFlag, fail_cases)

    def test_bad_option_str_combos(self):
        cases = [{'alt_short': '-B'}, {'alt_long': '--baz'}, {'alt_long': '--baz', 'alt_short': '-B'}]
        for case in cases:
            with self.subTest(case=case):

                class Foo(Command):
                    bar = TriFlag('-b', **case)
                    baz = Flag('-B')

                with self.assertRaisesRegex(CommandDefinitionError, 'option=.* conflict for command='):
                    Foo.parse([])

    def test_no_alt_short(self):
        class Foo(Command):
            spam = TriFlag('-s')

        self.assertSetEqual({'--no-spam'}, Foo.spam.option_strs.alt_allowed)

    # endregion

    # region Name Mode

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

        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
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

        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
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

        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
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

    def test_name_none_missing_options(self):
        cases = [((), {}), (('-b',), {}), ((), {'alt_short': '-B'})]
        for args, kwargs in cases:
            with self.subTest(args=args, kwargs=kwargs):

                class Foo(Command, option_name_mode=None):
                    bar = TriFlag(*args, **kwargs)

                with self.assertRaisesRegex(ParameterDefinitionError, 'No option strings were registered'):
                    Foo().parse([])

    def test_name_none(self):
        class Foo(Command, option_name_mode='NONE'):
            bar = TriFlag('-b', alt_short='-B')

        never_expected = ('--bar', '--no-bar', '--no_bar')
        help_text, usage_text = get_help_text(Foo), get_usage_text(Foo)
        self.assertTrue(all(val not in help_text for val in never_expected))
        self.assertTrue(all(val not in usage_text for val in never_expected))
        self.assertRegex(help_text, STANDALONE_DASH_B_LC)
        self.assertRegex(help_text, STANDALONE_DASH_B_UC)

        success_cases = [([], {'bar': None}), (['-b'], {'bar': True}), (['-B'], {'bar': False})]
        self.assert_parse_results_cases(Foo, success_cases)
        fail_cases = [['--bar'], ['--no-bar'], ['--no_bar']]
        self.assert_argv_parse_fails_cases(Foo, fail_cases)

    # endregion


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
