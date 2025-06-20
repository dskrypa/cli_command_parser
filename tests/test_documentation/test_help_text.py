#!/usr/bin/env python

from __future__ import annotations

from abc import ABC
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Sequence
from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser import Command, Context, ShowDefaults, no_exit_handler
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import MissingArgument
from cli_command_parser.formatting.commands import CommandHelpFormatter, get_usage_sub_cmds
from cli_command_parser.formatting.params import ChoiceGroup, ParamHelpFormatter, PositionalHelpFormatter
from cli_command_parser.formatting.restructured_text import RstTable
from cli_command_parser.inputs import Date, Day
from cli_command_parser.parameters import Counter, Flag, Option, ParamGroup, PassThru, Positional, TriFlag, action_flag
from cli_command_parser.parameters.choice_map import Action, Choice, ChoiceMap, SubCommand
from cli_command_parser.testing import (
    ParserTest,
    RedirectStreams,
    get_help_text,
    get_rst_text,
    get_usage_text,
    sealed_mock,
)

if TYPE_CHECKING:
    from cli_command_parser.typing import CommandCls

TEST_DESCRIPTION = 'This is a test description'
TEST_EPILOG = 'This is a test epilog'


class MetadataTest(ParserTest):
    def test_prog(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', add_help=True):
            action = Action()
            action(sealed_mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('usage: foo.py {bar}'), f'Unexpected stdout: {stdout}')
        self.assertNotIn(TEST_DESCRIPTION, stdout)
        self.assertNotIn(TEST_EPILOG, stdout)
        self.assertIn('Actions:', stdout)
        self.assertIn('Optional arguments:', stdout)
        self.assertIn('--help, -h', stdout)

    def test_explicit_usage(self):
        class Foo(Command, error_handler=no_exit_handler, usage='this is a test'):
            action = Action()
            action(sealed_mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('this is a test'), f'Unexpected stdout: {stdout}')
        self.assertNotIn('bar', stdout.splitlines()[0])

    def test_description(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', description=TEST_DESCRIPTION):
            action = Action()
            action(sealed_mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('usage: foo.py {bar}'), f'Unexpected stdout: {stdout}')
        self.assertIn(f'\n{TEST_DESCRIPTION}\n', stdout)

    def test_epilog(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', epilog=TEST_EPILOG):
            action = Action()
            action(sealed_mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('usage: foo.py {bar}'), f'Unexpected stdout: {stdout}')
        self.assertTrue(stdout.endswith(f'\n{TEST_EPILOG}\n'), f'Unexpected stdout: {stdout}')


class ParsedInvocationTest(ParserTest):
    def test_help_called_with_missing_required_params(self):
        help_mock = Mock()

        class Foo(Command, add_help=False):
            help = action_flag('-h', order=float('-inf'), always_available=True)(help_mock)
            bar = Option(required=True)

        Foo.parse_and_run(['-h'])
        self.assertTrue(help_mock.called)

    def test_help_called_with_missing_required_group(self):
        help_mock = Mock()

        class Foo(Command, add_help=False):
            help = action_flag('-h', order=float('-inf'), always_available=True)(help_mock)
            with ParamGroup(mutually_exclusive=True, required=True):
                bar = Option()
                baz = Option()

        Foo.parse_and_run(['-h'])
        self.assertTrue(help_mock.called)

    def test_help_called_with_unrecognized_args(self):
        when_cases_map = {
            'before': (['--foo', '-h'], ['-f', '1', '-h'], ['f', '--help']),
            'after': (['-h', '--foo'], ['-h', '-f', '1'], ['--help', 'f']),
        }
        for when, cases in when_cases_map.items():
            for case in cases:
                with self.subTest(when=when, case=case):
                    help_mock = Mock()

                    class Foo(Command, add_help=False):
                        help = action_flag('-h', order=float('-inf'), always_available=True)(help_mock)
                        with ParamGroup(mutually_exclusive=True, required=True):
                            bar = Option()
                            baz = Option()

                    Foo.parse_and_run(case)
                    self.assertTrue(help_mock.called)


class UsageTextTest(ParserTest):
    def test_pass_thru_usage(self):
        class Foo(Command):
            foo = Option()
            bar = PassThru()

        help_text = get_help_text(Foo)
        self.assertIn('--foo', help_text)
        self.assertIn('[-- BAR]', help_text)

    def test_usage_lambda_type(self):
        class Foo(Command, use_type_metavar=True):
            bar = Option(type=lambda v: v * 2)
            baz = Option(type=int)

        usage_text = get_usage_text(Foo)
        self.assertIn('--bar BAR', usage_text)
        self.assertIn('--baz INT', usage_text)

    def test_usage_no_name(self):
        class NoName:  # Note: PropertyMock does not work with side_effect=AttributeError
            @property
            def __name__(self):
                raise AttributeError

        class Foo(Command, use_type_metavar=True):
            bar = Option(type=NoName())  # noqa
            baz = Option(type=int)

        usage_text = get_usage_text(Foo)
        self.assertIn('--bar BAR', usage_text)
        self.assertIn('--baz INT', usage_text)

    def test_tri_flag_full_usage(self):
        class Foo(Command):
            spam = TriFlag('-s')

        self.assertEqual('--spam, -s | --no-spam', Foo.spam.format_usage(full=True))

    def test_non_subcommand_cmd_subclass_usage(self):
        class Foo(Command, prog='foo.py'):
            bar = Positional()

        class Baz(Foo):
            pass

        self.assertEqual('usage: foo.py BAR [--help]', get_usage_text(Foo))
        self.assertEqual('usage: foo.py BAR [--help]', get_usage_text(Baz))

    def test_wrapped_usage_explicit(self):
        usage = 'usage: foo_bar.py [--abcdef ABCDEF] [--ghijkl GHIJKL] [--mnopqr MNOPQR] [--stuvwx STUVWX] [--yz YZ]'

        class Foo(Command, wrap_usage_str=50, usage=usage):
            pass

        expected = """\
usage: foo_bar.py [--abcdef ABCDEF] [--ghijkl
    GHIJKL] [--mnopqr MNOPQR] [--stuvwx STUVWX]
    [--yz YZ]"""
        self.assert_strings_equal(expected, get_usage_text(Foo))

    def test_nargs_plus_usage(self):
        class Foo(Command, prog='foo.py'):
            bar = Option(nargs='+')

        self.assert_strings_equal('usage: foo.py [--bar BAR [BAR ...]] [--help]', get_usage_text(Foo))

    # def test_nargs_star_usage(self):
    #     class Foo(Command, prog='foo.py'):
    #         bar = Option(nargs='*')
    #
    #     self.assert_strings_equal('usage: foo.py [--bar [BAR ...]] [--help]', get_usage_text(Foo))


class HelpTextTest(ParserTest):
    def test_custom_choice_map(self):
        class Custom(ChoiceMap):
            pass

        with patch('cli_command_parser.utils.get_terminal_size', return_value=(123, 1)):
            self.assertTrue(Custom().formatter.format_help().startswith('Choices:'))
            self.assertTrue(Custom().format_help().startswith('Choices:'))

    def test_option_with_choices(self):
        obj_types = ('track', 'artist', 'album', 'tracks', 'artists', 'albums')
        # fmt: off
        printer_formats = [
            'json', 'json-pretty', 'json-compact', 'text', 'yaml', 'pprint', 'csv', 'table',
            'pseudo-yaml', 'json-lines', 'plain', 'pseudo-json',
        ]
        # fmt: on

        class Base(Command):
            sub = SubCommand()

        class Find(Base, help='Find information'):
            obj_type = Positional(choices=obj_types, help='Object type')
            title = Positional(nargs='*', help='Object title (optional)')
            escape = Option('-e', default='()', help='Escape the provided regex special characters')
            allow_inst = Flag('-I', help='Allow search results that include instrumental versions of songs')
            full_info = Flag('-F', help='Print all available info about the discovered objects')
            format = Option('-f', choices=printer_formats, default='yaml', help='Output format to use for --full_info')
            test = Option('-t', help=','.join(f'{i} extra long help text example' for i in range(10)))
            xl = Option('-x', choices=printer_formats, help=','.join(f'{i} extra long help text' for i in range(10)))

        expected = """Optional arguments:
  --help, -h                  Show this help message and exit
  --escape ESCAPE, -e ESCAPE  Escape the provided regex special characters (default: '()')
  --allow-inst, -I            Allow search results that include instrumental versions of songs
  --full-info, -F             Print all available info about the discovered objects
  --format {json|json-pretty|json-compact|text|yaml|pprint|csv|table|pseudo-yaml|json-lines|plain|pseudo-json},
    -f {json|json-pretty|json-compact|text|yaml|pprint|csv|table|pseudo-yaml|json-lines|plain|pseudo-json}
                              Output format to use for --full_info (default: 'yaml')
  --test TEST, -t TEST        0 extra long help text example,1 extra long help text example,2 extra long help text example,3 extra long help text example,4 extra long help text example,5 extra long
                              help text example,6 extra long help text example,7 extra long help text example,8 extra long help text example,9 extra long help text example"""

        help_text = get_help_text(Base.parse(['find', '-h']))
        self.assert_str_contains(expected, help_text)

    def test_subcommands_with_common_base_options_spacing(self):
        class Foo(Command, prog='foo.py'):
            sub_cmd = SubCommand()
            abc = Flag()

        class Bar(Foo):
            pass

        class Baz(Foo):
            pass

        expected = """
usage: foo.py {bar|baz} [--abc] [--help]

Subcommands:
  {bar|baz}
    bar
    baz

Optional arguments:
  --abc
  --help, -h                  Show this help message and exit
        """.lstrip()
        self.assert_strings_equal(expected, get_help_text(Foo), trim=True)

    def test_underscore_and_dash_enabled(self):
        class Foo(Command, option_name_mode='both'):
            foo_bar = Flag()

        help_text = get_help_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo_bar', help_text)

    def test_only_dash_enabled(self):
        class Foo(Command, option_name_mode='dash'):
            foo_bar = Flag()

        help_text = get_help_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertNotIn('--foo_bar', help_text)

    def test_only_underscore_enabled(self):
        class Foo(Command, option_name_mode='_'):
            foo_bar = Flag()

        help_text = get_help_text(Foo)
        self.assertIn('--foo_bar', help_text)
        self.assertNotIn('--foo-bar', help_text)

    def test_option_name_mode_overrides(self):
        mode_exp_map = {'underscore': ('--foo_a',), 'dash': ('--foo-a',), 'both': ('--foo-a', '--foo_a')}
        base_expected = ('--foo_b', '--foo-c', '--foo-d', '--foo_d', '--eeee', '-ff', '-fg')
        never_expected = ('--foo-e', '--foo_e', '--foo-f', '--foo_f', '--foo-g', '--foo_g')
        for mode, expected_a in mode_exp_map.items():
            with self.subTest(mode=mode):

                class Foo(Command, option_name_mode=mode):
                    foo_a = Flag()
                    foo_b = Flag(name_mode='underscore')
                    foo_c = Flag(name_mode='dash')
                    foo_d = Flag(name_mode='both')
                    foo_e = Flag('--eeee')
                    foo_f = Flag('-ff', name_mode=None)
                    foo_g = Flag('-fg', name_mode='NONE')

                help_text = get_help_text(Foo)
                self.assertTrue(all(exp in help_text for exp in base_expected))
                self.assertTrue(all(exp in help_text for exp in expected_a))
                self.assertTrue(all(val not in help_text for val in never_expected))

    def test_tri_flag_no_alt_short(self):
        class Foo(Command):
            spam = TriFlag('-s')

        self.assertIn('--spam, -s\n    --no-spam\n', get_help_text(Foo))

    def test_tri_flag_alt_help(self):
        class Foo(Command):
            spam = TriFlag('-s', alt_short='-S', help='Spam me', alt_help='Do not spam me')

        expected_help = '  --spam, -s                  Spam me\n  --no-spam, -S               Do not spam me\n'
        self.assert_str_contains(expected_help, get_help_text(Foo))
        expected_rst = """
    +-----------------------+---------------------------------+
    | ``--spam``, ``-s``    | Spam me                         |
    +-----------------------+---------------------------------+
    | ``--no-spam``, ``-S`` | Do not spam me                  |
    +-----------------------+---------------------------------+
    | ``--help``, ``-h``    | Show this help message and exit |
    +-----------------------+---------------------------------+
        """
        self.assert_str_contains(expected_rst.strip(), get_rst_text(Foo))

    def test_wide_text_line_wrap(self):
        class Foo(Command):
            bar = Option('-b', help='하나, 둘, 셋, 넷, 다섯, 여섯, 일곱, 여덟, 아홉, 열')

        expected = (
            '  --bar BAR, -b BAR           하나, 둘, 셋, 넷, 다섯,\n'
            '                              여섯, 일곱, 여덟, 아홉,\n'
            '                              열'
        )
        self.assert_str_contains(expected, get_help_text(Foo, 53))

    def test_date_input_metavar_sort_order(self):
        cases = [
            (False, '[--dow {Mon|Tue|Wed|Thu|Fri|Sat|Sun|0|1|2|3|4|5|6}] [--date {%Y-%m-%d|%Y-%m}]'),
            (True, '[--dow {0|1|2|3|4|5|6|Fri|Mon|Sat|Sun|Thu|Tue|Wed}] [--date {%Y-%m|%Y-%m-%d}]'),
        ]
        for sort_choices, expected in cases:
            with self.subTest(sort_choices=sort_choices):

                class Foo(Command, sort_choices=sort_choices):
                    dow = Option('-w', type=Day(numeric=True, full=False))
                    date = Option('-d', type=Date('%Y-%m-%d', '%Y-%m'))

                self.assert_str_contains(expected, get_usage_text(Foo))

    def test_flag_show_default_override(self):
        cases = [
            ({}, '--bar, -b\n'),
            ({'show_default': False}, '--bar, -b\n'),
            ({'show_default': True}, '--bar, -b                   (default: False)\n'),
        ]
        for kwargs, expected_text in cases:
            with self.subTest(kwargs=kwargs):

                class Foo(Command):
                    bar = Flag('-b', **kwargs)

            self.assert_str_contains(expected_text, get_help_text(Foo))

    def test_wrapped_usage_auto_width(self):
        class Foo(Command, wrap_usage_str=True, prog='foo_bar.py'):
            abcdef = Option()
            ghijkl = Option()
            mnopqr = Option()
            stuvwx = Option()
            yz = Option()

        expected = """\
usage: foo_bar.py [--abcdef ABCDEF]
    [--ghijkl GHIJKL] [--mnopqr MNOPQR]
    [--stuvwx STUVWX] [--yz YZ]"""
        self.assert_str_contains(expected, get_help_text(Foo, 50))

    def test_positional_nargs_metavars(self):
        for nargs, metavar in {'?': '[BAR]', '+': 'BAR [BAR ...]', '*': '[BAR ...]'}.items():
            with self.subTest(nargs=nargs):

                class Foo(Command):
                    bar = Positional(nargs=nargs)

                self.assert_str_contains(f'Positional arguments:\n  {metavar}\n', get_help_text(Foo))

    # region Show Env Vars

    def test_env_vars_shown(self):
        class Cmd(Command):
            foo = Option('-f', env_var='FOO', help='The foo to foo')
            bar = Option('-b', env_var=('BAR', 'BAZ'), help='What to bar')

        expected = """
  --foo FOO, -f FOO           The foo to foo (may be provided via env var: FOO)
  --bar BAR, -b BAR           What to bar (may be provided via any of the following env vars: BAR, BAZ)
        """.rstrip()
        self.assert_str_contains(expected, get_help_text(Cmd))

    def test_env_vars_not_shown(self):
        class Cmd(Command, show_env_vars=False):
            foo = Option('-f', env_var='FOO', help='The foo to foo')
            bar = Option('-b', env_var=('BAR', 'BAZ'), help='What to bar')

        expected = '  --foo FOO, -f FOO           The foo to foo\n  --bar BAR, -b BAR           What to bar\n'
        self.assert_str_contains(expected, get_help_text(Cmd))

    def test_one_env_var_not_shown(self):
        class Cmd(Command):
            foo = Option('-f', env_var='FOO', help='The foo to foo', show_env_var=False)
            bar = Option('-b', env_var=('BAR', 'BAZ'), help='What to bar')

        expected = """
  --foo FOO, -f FOO           The foo to foo
  --bar BAR, -b BAR           What to bar (may be provided via any of the following env vars: BAR, BAZ)
        """.rstrip()
        self.assert_str_contains(expected, get_help_text(Cmd))

    def test_one_env_var_shown(self):
        class Cmd(Command, show_env_vars=False):
            foo = Option('-f', env_var='FOO', help='The foo to foo', show_env_var=True)
            bar = Option('-b', env_var=('BAR', 'BAZ'), help='What to bar')

        expected = """
  --foo FOO, -f FOO           The foo to foo (may be provided via env var: FOO)
  --bar BAR, -b BAR           What to bar
        """.rstrip()
        self.assert_str_contains(expected, get_help_text(Cmd))

    # endregion

    def test_long_usage_parts_with_no_desc_wrapped(self):
        class Foo(Command, strict_usage_column_width=True):
            bar = Option('-b', metavar='BAR_BAR_BAR_BAR_BAR')

        self.assert_str_contains('\n  --bar BAR_BAR_BAR_BAR_BAR,\n    -b BAR_BAR_BAR_BAR_BAR\n', get_help_text(Foo))

    def test_long_usage_parts_with_no_desc_not_wrapped(self):
        class Foo(Command):
            bar = Option('-b', metavar='BAR_BAR_BAR_BAR_BAR')

        self.assert_str_contains('\n  --bar BAR_BAR_BAR_BAR_BAR, -b BAR_BAR_BAR_BAR_BAR\n', get_help_text(Foo))

    def test_long_1_part_usage_with_desc_wrapped(self):
        class Foo(Command):
            bar = Option(metavar='BAR_BAR_BAR_BAR_BAR_B', help='The bar to baz')

        # This usage string would leave only 1 space between the usage and description
        expected = '\n  --bar BAR_BAR_BAR_BAR_BAR_B\n' + ' ' * 30 + 'The bar to baz\n'
        self.assert_str_contains(expected, get_help_text(Foo))

    def test_long_1_part_usage_with_desc_not_wrapped(self):
        class Foo(Command):
            bar = Option(metavar='BAR_BAR_BAR_BAR_BAR_', help='The bar to baz')  # 1 less char than the above test

        self.assert_str_contains('\n  --bar BAR_BAR_BAR_BAR_BAR_  The bar to baz\n', get_help_text(Foo))

    def test_test_long_usage_parts_with_long_desc_wrapped(self):
        class Foo(Command, strict_usage_column_width=True):
            bar = Option('-b', metavar='BAR_BAR_BAR_BAR_BAR', help='The bar to baz or the foo to bar and baz')

        # fmt: off
        expected = (
            '\n  --bar BAR_BAR_BAR_BAR_BAR,  The bar to baz or the'
            '\n    -b BAR_BAR_BAR_BAR_BAR    foo to bar and baz\n'
        )
        # fmt: on
        self.assert_str_contains(expected, get_help_text(Foo, terminal_width=52))


class SubcommandHelpAndRstTest(ParserTest):
    @contextmanager
    def assert_help_and_rst_match(
        self,
        mode: str,
        param_help_map: dict[str, str],
        help_header: str,
        cmd_mode: str = None,
        sc_kwargs: dict[str, Any] = None,
        cmd_kwargs: dict[str, Any] = None,
    ) -> Iterator[CommandCls]:
        if not cmd_kwargs:
            cmd_kwargs = {}
        if cmd_mode:
            cmd_kwargs['cmd_alias_mode'] = cmd_mode
        if not sc_kwargs:
            sc_kwargs = {}

        with self.subTest(mode=mode, **cmd_kwargs):
            expected_help = prep_expected_help_text(help_header, param_help_map)
            expected_rst = prep_expected_rst('    {:<13s}', param_help_map)

            class Foo(Command, **cmd_kwargs):
                sub_cmd = SubCommand(**sc_kwargs)

            yield Foo

            self.assert_str_contains(expected_help, get_help_text(Foo))
            self.assert_str_contains(expected_rst, get_rst_text(Foo))

    def test_subcommand_is_in_usage(self):
        class Foo(Command, prog='foo.py'):
            sub = SubCommand()

        class Bar(Foo):
            pass

        class Baz(Foo):
            pos = Positional()

        self.assertEqual('usage: foo.py bar [--help]', get_usage_text(Bar))
        self.assertEqual('usage: foo.py baz POS [--help]', get_usage_text(Baz))

    def test_middle_abc_subcommand_is_in_usage(self):
        class Foo(Command, prog='foo.py'):
            sub = SubCommand()

        class Mid(Foo, ABC):
            pass

        class Bar(Mid):
            pos = Positional()

        self.assertEqual('usage: foo.py bar POS [--help]', get_usage_text(Bar))

    def test_nested_subcommand_is_in_usage(self):
        class Foo(Command, prog='foo.py'):
            sub_a = SubCommand()

        class Bar(Foo):
            sub_b = SubCommand()

        class Baz(Bar):
            pass

        self.assertEqual('usage: foo.py bar {baz} [--help]', get_usage_text(Bar))
        self.assertEqual('usage: foo.py bar baz [--help]', get_usage_text(Baz))

    def test_subcommand_choice_alias_modes(self):
        help_header = 'Subcommands:\n  {bar|bars|baz}\n'
        foo_help, bar_help, baz_help = 'Foo the foo', 'Foo one or more bars', 'Foo one or more baz'
        cases = (
            ('alias', {'(default)': foo_help, 'bar': bar_help, 'bars': 'Alias of: bar', 'baz': baz_help}),
            ('repeat', {'(default)': foo_help, 'bar': bar_help, 'bars': bar_help, 'baz': baz_help}),
            ('combine', {'(default)': foo_help, '{bar|bars}': bar_help, 'baz': baz_help}),
        )
        sub_cmd_kwargs = {'required': False, 'default_help': 'Foo the foo'}
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode, sub_cmd_kwargs) as Foo:

                class Bar(Foo, choices=('bar', 'bars'), help='Foo one or more bars'):
                    abc = Flag('-a')

                class Baz(Foo, help='Foo one or more baz'):
                    xyz = Flag('-x')

    def test_subcommand_choice_alias_modes_on_subcmd(self):
        help_header = 'Subcommands:\n  {bar|bars|baz|bazs}\n'
        bar_help, bars_help, baz_help = 'Foo one or more bars', 'Alias of: bar', 'Foo one or more baz'
        cases = (
            ('alias', {'bar': bar_help, 'bars': bars_help, 'baz': baz_help, 'bazs': 'Alias of: baz'}),
            ('repeat', {'bar': bar_help, 'bars': bars_help, 'baz': baz_help, 'bazs': baz_help}),
            ('combine', {'bar': bar_help, 'bars': bars_help, '{baz|bazs}': baz_help}),
        )
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header) as Foo:

                class Bar(Foo, choices=('bar', 'bars'), help='Foo one or more bars', cmd_alias_mode='alias'):
                    abc = Flag('-a')

                class Baz(Foo, choices=('baz', 'bazs'), help='Foo one or more baz', cmd_alias_mode=mode):
                    xyz = Flag('-x')

    def test_subcommand_alias_custom_help_retained(self):
        help_header = 'Subcommands:\n  {bar|run bar}\n'
        expected = {'bar': 'Execute bar', 'run bar': 'Run bar'}
        cases = (('alias', expected), ('repeat', expected), ('combine', expected))
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode) as Foo:

                @Foo.sub_cmd.register('run bar', help='Run bar')
                class Bar(Foo, help='Execute bar'):
                    pass

    def test_subcommand_local_choices(self):
        help_header = 'Subcommands:\n  {a|b|c}\n'
        choice_map = {'a': 'Find As', 'b': 'Find Bs', 'c': 'Find Cs'}
        local_cases = (
            (choice_map, {'local_choices': choice_map}),
            ({'a': '', 'b': '', 'c': ''}, {'local_choices': ('a', 'b', 'c')}),
        )
        for expected, sc_kwargs in local_cases:
            cases = (('alias', expected), ('repeat', expected), ('combine', expected))
            for mode, param_help_map in cases:
                with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode, sc_kwargs):
                    pass

    def test_subcommand_choices_map(self):
        help_header = 'Subcommands:\n  {a|b|c|d}\n'
        a, b, bar = 'Find As', 'Find Bs', 'Execute bar'
        choice_map = {'a': a, 'b': b, 'c': None, 'd': ''}
        for bar_help, bar_exp in ((None, ''), (bar, bar)):
            cases = (
                ('alias', {'a': a, 'b': b, 'c': bar_exp, 'd': 'Alias of: c'}),
                ('repeat', {'a': a, 'b': b, 'c': bar_exp, 'd': bar_exp}),
                ('combine', {'a': a, 'b': b, '{c|d}': bar_exp}),
            )
            for mode, param_help_map in cases:
                with self.subTest(bar_help=bar_help):
                    with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode) as Foo:

                        class Bar(Foo, choices=choice_map, help=bar_help):
                            pass

    def test_subcommand_choices_map_custom_format(self):
        help_header = 'Subcommands:\n  {a|b|c|d}\n'
        a, b, c, bar = 'Find As', 'Find Bs', 'Find Cs', 'Execute bar'
        fmt_a, fmt_b = '{help} [Alias of: {choice}]', 'Test {alias}'
        cases = (
            (fmt_a, {'a': a, 'b': b, 'c': None, 'd': ''}, {'a': a, 'b': b, 'c': bar, 'd': f'{bar} [Alias of: c]'}),
            (fmt_a, {'a': a, 'b': b, 'c': c, 'd': c}, {'a': a, 'b': b, 'c': c, 'd': f'{c} [Alias of: c]'}),
            (fmt_b, {'a': a, 'b': b, 'c': c, 'd': c}, {'a': a, 'b': b, 'c': c, 'd': 'Test d'}),
        )
        for fmt_str, choice_map, param_help_map in cases:
            with self.assert_help_and_rst_match('alias', param_help_map, help_header) as Foo:

                class Bar(Foo, choices=choice_map, help=bar, cmd_alias_mode=fmt_str):
                    pass

    def test_subcommand_choices_sort_order(self):
        a, b, c, bar = 'Find As', 'Find Bs', 'Find Cs', 'Execute bar'
        choice_map = {'d': c, 'b': b, 'a': a, 'c': c}
        cases = (
            (False, 'Subcommands:\n  {d|c|b|a}\n', {'d': c, 'c': c, 'b': b, 'a': a}),  # c moves due to group
            (True, 'Subcommands:\n  {a|b|c|d}\n', {'a': a, 'b': b, 'c': c, 'd': c}),
        )
        for sort_choices, help_header, param_help_map in cases:
            cmd_kwargs = {'sort_choices': sort_choices, 'cmd_alias_mode': 'repeat'}
            with self.assert_help_and_rst_match('repeat', param_help_map, help_header, cmd_kwargs=cmd_kwargs) as Foo:

                class Bar(Foo, choices=choice_map, help=bar):
                    pass


def prep_expected_help_text(help_header: str, param_help_map: dict[str, str], indent: int = 4) -> str:
    prefix = ' ' * indent
    kf = f'{prefix}{{:s}}\n'.format
    hf = f'{prefix}{{:<25s}} {{}}\n'.format
    return help_header + ''.join(hf(k, v) if v else kf(k) for k, v in param_help_map.items())


def prep_expected_rst(table_fmt_str: str, param_help_map: dict[str, str]) -> str:
    rf = table_fmt_str.format
    table = RstTable.from_dict({f'``{k}``': v for k, v in param_help_map.items()}, use_table_directive=False)
    return '\n'.join(rf(line).rstrip() for line in table.iter_build() if line)


class ShowDefaultsTest(TestCase):
    def assert_default_x_in_help_text(self, defaults: Iterable[Any], expect_in: bool, check_str: str = None, **kwargs):
        for default in defaults:
            with self.subTest(default=default, expect_in=expect_in):
                default_str = check_str or f'(default: {default!r})'
                help_text = Option(default=default, **kwargs).formatter.format_help()
                self.assertEqual(expect_in, default_str in help_text)

    def test_sd_any_shows_all_defaults(self):
        cases = [0, 1, 'test', False, True, (), [], '', None]
        with Context(show_defaults='any'):
            self.assertNotIn('default:', Option(required=True).formatter.format_help())
            self.assert_default_x_in_help_text(cases, True)
            self.assert_default_x_in_help_text(cases, True, show_default=True)
            self.assert_default_x_in_help_text(cases, False, show_default=False, check_str='default:')

    def test_sd_any_missing_adds_no_defaults(self):
        cases = [0, 1, 'test', False, True, (), [], '', None]
        with Context(show_defaults=ShowDefaults.ANY | ShowDefaults.MISSING):
            self.assertNotIn('default:', Option(required=True).formatter.format_help())
            self.assert_default_x_in_help_text(cases, True)
            self.assert_default_x_in_help_text(cases, False, help='default: fake')
            self.assert_default_x_in_help_text(cases, True, show_default=True)
            self.assert_default_x_in_help_text(cases, False, show_default=False, check_str='default:')

    def test_sd_non_empty_shows_falsey_non_empty_defaults(self):
        in_cases = [0, 1, 'test', False, True]
        not_in_cases = [(), [], '', None]

        with Context(show_defaults='non-empty'):
            self.assertNotIn('default:', Option(required=True).formatter.format_help())
            self.assert_default_x_in_help_text(in_cases, True)
            self.assert_default_x_in_help_text(not_in_cases, False, check_str='default:')
            self.assert_default_x_in_help_text(in_cases, True, show_default=True)
            self.assert_default_x_in_help_text(not_in_cases, True, show_default=True)
            self.assert_default_x_in_help_text(in_cases, False, show_default=False, check_str='default:')
            self.assert_default_x_in_help_text(not_in_cases, False, show_default=False, check_str='default:')

    def test_sd_truthy_shows_only_truthy_defaults(self):
        in_cases = [1, 'test', True]
        not_in_cases = [0, False, (), [], '', None]

        with Context(show_defaults='truthy'):
            self.assertNotIn('default:', Option(required=True).formatter.format_help())
            self.assert_default_x_in_help_text(in_cases, True)
            self.assert_default_x_in_help_text(not_in_cases, False, check_str='default:')
            self.assert_default_x_in_help_text(in_cases, True, show_default=True)
            self.assert_default_x_in_help_text(not_in_cases, True, show_default=True)
            self.assert_default_x_in_help_text(in_cases, False, show_default=False, check_str='default:')
            self.assert_default_x_in_help_text(not_in_cases, False, show_default=False, check_str='default:')


class GroupHelpTextTest(ParserTest):
    def test_group_description(self):
        class Foo(Command, error_handler=no_exit_handler):
            foo = ParamGroup(description='group foo')
            with ParamGroup(description='test group') as group:
                bar = Positional()
                baz = Positional()

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertIn('test group:', stdout.splitlines())
        self.assertNotIn('group foo:', stdout)
        self.assertNotIn('Positional arguments:', stdout)

    def test_empty_groups_hidden(self):
        class Base(Command):
            sub_cmd = SubCommand()
            verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        class Show(Base, choice='show', help='Show the results of an action'):
            action = Action(help='What to show')
            action(Mock(__name__='attrs'))
            action(Mock(__name__='hello'))
            action(Mock(__name__='log_test'))

        help_line = '  --help, -h                  Show this help message and exit'
        expected_sub_cmd = 'Subcommands:\n  {show}\n    show                      Show the results of an action'
        verbose_desc = 'Increase logging verbosity (can specify multiple times)'

        for use_type_metavar in (False, True):
            with self.subTest(use_type_metavar=use_type_metavar):
                CommandMeta.config(Base).use_type_metavar = use_type_metavar

                help_text = get_help_text(Base)
                self.assertNotIn('Positional arguments:', help_text)
                self.assertIn(expected_sub_cmd, help_text)

                help_lines = help_text.splitlines()
                opt_header_idx = help_lines.index('Optional arguments:')
                self.assertIn(help_line, help_lines[opt_header_idx:])

                if use_type_metavar:
                    self.assertIn(f'  --verbose [INT], -v [INT]   {verbose_desc}', help_lines[opt_header_idx:])
                else:
                    verbose_line_1_index = help_lines.index('  --verbose [VERBOSE], -v [VERBOSE]')
                    self.assertGreater(verbose_line_1_index, opt_header_idx)
                    self.assertIn((' ' * 30) + verbose_desc, help_lines[verbose_line_1_index:])

    def test_hidden_params_not_shown(self):
        class Foo(Command):
            bar = Option()
            baz = Flag(hide=True)

        self.assertFalse(Foo.bar.hide)
        self.assertTrue(Foo.baz.hide)
        self.assertTrue(Foo.bar.show_in_help)
        self.assertFalse(Foo.baz.show_in_help)

        help_text = get_help_text(Foo)
        rst_text = get_rst_text(Foo)
        self.assertIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)
        self.assertNotIn('--baz', rst_text)

    def test_hidden_groups_not_shown(self):
        class Foo(Command):
            foo = Option()
            with ParamGroup(hide=True) as outer:
                bar = Option()
                with ParamGroup() as inner:
                    baz = Flag()

        help_text = get_help_text(Foo)
        rst_text = get_rst_text(Foo())
        self.assertIn('--foo', help_text)
        self.assertNotIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)
        self.assertNotIn('--baz', rst_text)

    def test_anon_group_auto_names_not_used(self):
        expected = """
usage: ansi_color_test.py [--text TEXT] [--attr {bold|dim}] [--limit LIMIT] [--basic] [--hex] [--all] [--color COLOR] [--background BACKGROUND] [--help]

Tool for testing ANSI colors

Optional arguments:
  --text TEXT, -t TEXT        Text to be displayed (default: the number of the color being shown)
  --attr {bold|dim}, -a {bold|dim}
                              Background color to use (default: None)
  --limit LIMIT, -L LIMIT     Range limit (default: 256)
  --help, -h                  Show this help message and exit

Mutually exclusive options:
  --basic, -B                 Display colors without the 38;5; prefix (cannot be combined with other args)
  --hex, -H                   Display colors by hex value (cannot be combined with other args)
  --all, -A                   Show all foreground and background colors (only when no color/bg is specified)

Optional arguments:
  --color COLOR, -c COLOR     Text color to use (default: cycle through 0-256)
  --background BACKGROUND, -b BACKGROUND
                              Background color to use (default: None)
        """.lstrip()

        class AnsiColorTest(Command, description='Tool for testing ANSI colors', prog='ansi_color_test.py'):
            text = Option('-t', help='Text to be displayed (default: the number of the color being shown)')
            attr = Option('-a', choices=('bold', 'dim'), help='Background color to use (default: None)')
            limit: int = Option('-L', default=256, help='Range limit')

            with ParamGroup(mutually_exclusive=True):
                basic = Flag('-B', help='Display colors without the 38;5; prefix (cannot be combined with other args)')
                hex = Flag('-H', help='Display colors by hex value (cannot be combined with other args)')
                all = Flag('-A', help='Show all foreground and background colors (only when no color/bg is specified)')
                with ParamGroup():  # Both of these can be provided, but neither can be combined with --all / -A
                    color = Option('-c', help='Text color to use (default: cycle through 0-256)')
                    background = Option('-b', help='Background color to use (default: None)')

        self.assert_strings_equal(expected, get_help_text(AnsiColorTest), diff_lines=7, trim=True)

    def test_nested_show_tree(self):
        expected_fmt = """
usage: foo.py [--foo FOO] [--arg-a ARG_A] [--arg-b ARG_B] [--arg-y Y_VALUE] [--arg-z Z_VALUE] [--bar] [--baz] [--help]

Optional arguments:
{o}--foo FOO, -f FOO         {i}Do foo
{o}--help, -h                {i}Show this help message and exit
{o}
Mutually exclusive options:
{e}--arg-a ARG_A, -a ARG_A   {i}A
{e}--arg-b ARG_B, -b ARG_B   {i}B
{e}
{eh}Mutually dependent options:
{ed}--arg-y Y_VALUE, -y Y_VALUE
{ed}{s}                      Y
{ed}--arg-z Z_VALUE, -z Z_VALUE
{ed}{s}                      Z
{ed}
{e}
{eh}Optional arguments:
{eo}--bar
{eo}--baz
{eo}
{e}
        """.strip()

        cases = [
            ((), {'e': '¦ ', 'd': '║ ', 'o': '│ '}),
            (('¦', '║', '│'), {'e': '¦ ', 'd': '║ ', 'o': '│ '}),
            (('~ ', '+ ', '@ '), {'e': '~ ', 'd': '+ ', 'o': '@ '}),
            (('~~~', '+++', '@@@'), {'e': '~~~ ', 'd': '+++ ', 'o': '@@@ ', 's': '', 'i': ''}),
            (('  ', '  ', '  '), {'e': '  ', 'd': '  ', 'o': '  '}),
            ((' ', ' ', ' '), {'e': '  ', 'd': '', 'o': '  ', 's': '      ', 'ed': '  ', 'eo': '  ', 'eh': ' '}),
            (('', '', ''), {'e': '  ', 'd': '  ', 'o': '  ', 's': '      ', 'ed': '  ', 'eo': '  ', 'eh': ''}),
        ]
        for spacers, render_vars in cases:
            with self.subTest(spacers=spacers):
                kwargs = {'group_tree_spacers': spacers} if spacers else {}
                render_vars.setdefault('eh', render_vars['e'])
                render_vars.setdefault('ed', render_vars['e'] + render_vars['d'])
                render_vars.setdefault('eo', render_vars['e'] + render_vars['o'])
                render_vars.setdefault('s', '    ')
                render_vars.setdefault('i', '  ')

                expected = '\n'.join(map(str.rstrip, expected_fmt.format(**render_vars).splitlines()))

                class Foo(Command, show_group_tree=True, prog='foo.py', **kwargs):
                    foo = Option('-f', help='Do foo')
                    with ParamGroup(mutually_exclusive=True):
                        arg_a = Option('-a', help='A')
                        arg_b = Option('-b', help='B')
                        with ParamGroup(mutually_dependent=True):
                            arg_y = Option('-y', metavar='Y_VALUE', help='Y')
                            arg_z = Option('-z', metavar='Z_VALUE', help='Z')
                        with ParamGroup():
                            bar = Flag()
                            baz = Flag()

                help_text = get_help_text(Foo).rstrip()
                self.assert_strings_equal(expected, help_text, diff_lines=7, trim=True)


class FormatterTest(ParserTest):
    def test_get_usage_sub_cmds_impossible(self):
        # This an impossible case that is purely for coverage

        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Command):
            pass

        with patch('cli_command_parser.core.CommandMeta.parent', lambda c, x=None: Foo if c is Bar else None):
            self.assertEqual([], list(get_usage_sub_cmds(Bar)))

    def test_non_base_formatter_cls_does_not_lookup_subclass(self):
        formatter = PositionalHelpFormatter(SubCommand())
        # Would be ChoiceMapHelpFormatter if it looked up the subclass
        self.assertIs(formatter.__class__, PositionalHelpFormatter)

    def test_default_formatter_class_returned(self):
        formatter = ParamHelpFormatter.for_param_cls(int)  # noqa
        self.assertIs(formatter, ParamHelpFormatter)

    def test_formatter_uses_cmd_ctx(self):
        class Foo(Command):
            bar = Option(required=True)

        foo = Foo()
        with self.assertRaises(MissingArgument):  # Accesses the formatter outside of parsing context
            foo.bar  # noqa

    def test_custom_formatter(self):
        class CustomFormatter(ParamHelpFormatter):
            def format_help(self, *args, **kwargs):
                return 'test help'

        class Foo(Command, param_formatter=CustomFormatter):
            bar = Flag()

        with Foo().ctx:
            self.assertEqual('test help', Foo.bar.format_help())

    def test_formatter_no_config(self):
        class Foo(ABC, metaclass=CommandMeta):
            pass

        self.assertIsInstance(CommandMeta.params(Foo).formatter, CommandHelpFormatter)

    def test_choice_group_add_no_str(self):
        group = ChoiceGroup(Choice(''))
        group.add(Choice(None))
        self.assertEqual(0, len(group.choice_strs))

    def test_group_desc_override(self):
        class Foo(Command):
            with ParamGroup() as group:
                bar = Option()

        self.assertEqual('test 12345', Foo.group.formatter.format_description(description='test 12345'))

    def test_required_default_group(self):
        class Foo(Command):
            out_path = Option('-o', required=True, help='Output file path')
            verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')
            dry_run = Flag('-D', help='Print the actions that would be taken instead of taking them')

        expected = """
Required arguments:
  --out-path OUT_PATH, -o OUT_PATH
                              Output file path

Optional arguments:
  --verbose [VERBOSE], -v [VERBOSE]
                              Increase logging verbosity (can specify multiple times)
  --dry-run, -D               Print the actions that would be taken instead of taking them
  --help, -h                  Show this help message and exit
        """.rstrip()
        self.assert_str_contains(expected, get_help_text(Foo))


def _get_output(command: CommandCls, args: Sequence[str]) -> tuple[str, str]:
    with RedirectStreams() as streams:
        command.parse_and_run(args)

    return streams.stdout, streams.stderr


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
