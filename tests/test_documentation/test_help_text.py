#!/usr/bin/env python

from __future__ import annotations

from abc import ABC
from contextlib import contextmanager
from textwrap import dedent
from typing import TYPE_CHECKING, Sequence, Iterable, Any, ContextManager, Tuple, Dict
from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser import Command, no_exit_handler, Context, ShowDefaults
from cli_command_parser.core import CommandMeta
from cli_command_parser.exceptions import MissingArgument
from cli_command_parser.formatting.commands import CommandHelpFormatter, get_usage_sub_cmds
from cli_command_parser.formatting.params import ParamHelpFormatter, PositionalHelpFormatter, ChoiceGroup
from cli_command_parser.formatting.restructured_text import RstTable
from cli_command_parser.parameters.choice_map import ChoiceMap, SubCommand, Action, Choice
from cli_command_parser.parameters import Positional, Counter, ParamGroup, Option, Flag, PassThru, action_flag, TriFlag
from cli_command_parser.testing import ParserTest, RedirectStreams, get_rst_text, get_help_text, get_usage_text

if TYPE_CHECKING:
    from cli_command_parser.typing import CommandCls

TEST_DESCRIPTION = 'This is a test description'
TEST_EPILOG = 'This is a test epilog'


class MetadataTest(ParserTest):
    def test_prog(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', add_help=True):
            action = Action()
            action(Mock(__name__='bar'))

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
            action(Mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('this is a test'), f'Unexpected stdout: {stdout}')
        self.assertNotIn('bar', stdout.splitlines()[0])

    def test_description(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', description=TEST_DESCRIPTION):
            action = Action()
            action(Mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('usage: foo.py {bar}'), f'Unexpected stdout: {stdout}')
        self.assertIn(f'\n{TEST_DESCRIPTION}\n', stdout)

    def test_epilog(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py', epilog=TEST_EPILOG):
            action = Action()
            action(Mock(__name__='bar'))

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(stdout.startswith('usage: foo.py {bar}'), f'Unexpected stdout: {stdout}')
        self.assertTrue(stdout.endswith(f'\n{TEST_EPILOG}\n'), f'Unexpected stdout: {stdout}')

    def test_subcommand_is_in_usage(self):
        class Foo(Command, prog='foo.py'):
            sub_cmd = SubCommand()

        class Bar(Foo):
            pass

        class Baz(Foo):
            pass

        usage = get_usage_text(Baz)
        self.assertEqual('usage: foo.py baz [--help]', usage)


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
            spam = TriFlag('-s', name_mode='-')

        self.assertEqual('--spam, -s | --no-spam', Foo.spam.format_usage(full=True))


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
  --help, -h                  Show this help message and exit (default: False)
  --escape ESCAPE, -e ESCAPE  Escape the provided regex special characters (default: '()')
  --allow_inst, -I            Allow search results that include instrumental versions of songs (default: False)
  --full_info, -F             Print all available info about the discovered objects (default: False)
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

        expected = dedent(
            """
            usage: foo.py {bar|baz} [--abc] [--help]

            Subcommands:
              {bar|baz}
                bar
                baz

            Optional arguments:
              --abc                       (default: False)
              --help, -h                  Show this help message and exit (default: False)
            """
        ).lstrip()
        help_text = get_help_text(Foo)
        self.assertEqual(expected, help_text)

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

    def test_option_name_mode_overrides(self):
        mode_exp_map = {'underscore': ('--foo_a',), 'dash': ('--foo-a',), 'both': ('--foo-a', '--foo_a')}
        base_expected = ('--foo_b', '--foo-c', '--foo-d', '--foo_d', '--eeee')
        for mode, expected_a in mode_exp_map.items():
            with self.subTest(mode=mode):

                class Foo(Command, option_name_mode=mode):
                    foo_a = Flag()
                    foo_b = Flag(name_mode='underscore')
                    foo_c = Flag(name_mode='dash')
                    foo_d = Flag(name_mode='both')
                    foo_e = Flag('--eeee')

                help_text = get_help_text(Foo)
                self.assertTrue(all(exp in help_text for exp in base_expected))
                self.assertTrue(all(exp in help_text for exp in expected_a))
                self.assertNotIn('--foo_e', help_text)
                self.assertNotIn('--foo-e', help_text)

    def test_tri_flag_no_alt_short(self):
        class Foo(Command):
            spam = TriFlag('-s', name_mode='-')

        self.assertIn('--spam, -s\n    --no-spam\n', get_help_text(Foo))

    def test_wide_text_line_wrap(self):
        class Foo(Command):
            bar = Option('-b', help='하나, 둘, 셋, 넷, 다섯, 여섯, 일곱, 여덟, 아홉, 열')

        expected = (
            '  --bar BAR, -b BAR           하나, 둘, 셋, 넷, 다섯,\n'
            '                              여섯, 일곱, 여덟, 아홉,\n'
            '                              열'
        )
        self.assert_str_contains(expected, get_help_text(Foo, 53))


class SubcommandHelpAndRstTest(ParserTest):
    @contextmanager
    def assert_help_and_rst_match(
        self,
        mode: str,
        param_help_map: Dict[str, str],
        help_header: str,
        cmd_mode: str = None,
        sc_kwargs: Dict[str, Any] = None,
    ) -> ContextManager[CommandCls]:
        with self.subTest(mode=mode):
            cmd_kwargs = {'cmd_alias_mode': cmd_mode} if cmd_mode else {}
            if not sc_kwargs:
                sc_kwargs = {}
            expected_help, expected_rst = get_expected_help_and_rst(help_header, param_help_map)

            class Foo(Command, **cmd_kwargs):
                sub_cmd = SubCommand(**sc_kwargs)

            yield Foo

            self.assert_str_contains(expected_help, get_help_text(Foo))
            self.assert_str_contains(expected_rst, get_rst_text(Foo))

    def test_sub_command_choice_alias_modes(self):
        help_header = 'Subcommands:\n  {bar|bars|baz}\n'
        foo_help, bar_help, baz_help = 'Foo the foo', 'Foo one or more bars', 'Foo one or more baz'
        cases = [
            ('alias', {'(default)': foo_help, 'bar': bar_help, 'bars': 'Alias of: bar', 'baz': baz_help}),
            ('repeat', {'(default)': foo_help, 'bar': bar_help, 'bars': bar_help, 'baz': baz_help}),
            ('combine', {'(default)': foo_help, '{bar|bars}': bar_help, 'baz': baz_help}),
        ]
        sub_cmd_kwargs = {'required': False, 'default_help': 'Foo the foo'}
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode, sub_cmd_kwargs) as Foo:

                class Bar(Foo, choices=('bar', 'bars'), help='Foo one or more bars'):
                    abc = Flag('-a')

                class Baz(Foo, help='Foo one or more baz'):
                    xyz = Flag('-x')

    def test_sub_command_choice_alias_modes_on_subcmd(self):
        help_header = 'Subcommands:\n  {bar|bars|baz|bazs}\n'
        bar_help, bars_help, baz_help = 'Foo one or more bars', 'Alias of: bar', 'Foo one or more baz'
        cases = [
            ('alias', {'bar': bar_help, 'bars': bars_help, 'baz': baz_help, 'bazs': 'Alias of: baz'}),
            ('repeat', {'bar': bar_help, 'bars': bars_help, 'baz': baz_help, 'bazs': baz_help}),
            ('combine', {'bar': bar_help, 'bars': bars_help, '{baz|bazs}': baz_help}),
        ]
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header) as Foo:

                class Bar(Foo, choices=('bar', 'bars'), help='Foo one or more bars', cmd_alias_mode='alias'):
                    abc = Flag('-a')

                class Baz(Foo, choices=('baz', 'bazs'), help='Foo one or more baz', cmd_alias_mode=mode):
                    xyz = Flag('-x')

    def test_sub_command_alias_custom_help_retained(self):
        help_header = 'Subcommands:\n  {bar|run bar}\n'
        expected = {'bar': 'Execute bar', 'run bar': 'Run bar'}
        cases = [('alias', expected), ('repeat', expected), ('combine', expected)]
        for mode, param_help_map in cases:
            with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode) as Foo:

                @Foo.sub_cmd.register('run bar', help='Run bar')
                class Bar(Foo, help='Execute bar'):
                    pass

    def test_subcommand_local_choices(self):
        help_header = 'Subcommands:\n  {a|b|c}\n'
        choice_map = {'a': 'Find As', 'b': 'Find Bs', 'c': 'Find Cs'}
        local_cases = [
            (choice_map, {'local_choices': choice_map}),
            ({'a': '', 'b': '', 'c': ''}, {'local_choices': ('a', 'b', 'c')}),
        ]
        for expected, sc_kwargs in local_cases:
            cases = [('alias', expected), ('repeat', expected), ('combine', expected)]
            for mode, param_help_map in cases:
                with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode, sc_kwargs):
                    pass

    def test_subcommand_choices_map(self):
        help_header = 'Subcommands:\n  {a|b|c|d}\n'
        a, b, bar = 'Find As', 'Find Bs', 'Execute bar'
        choice_map = {'a': a, 'b': b, 'c': None, 'd': ''}
        for bar_help, bar_exp in ((None, ''), (bar, bar)):
            cases = [
                ('alias', {'a': a, 'b': b, 'c': bar_exp, 'd': 'Alias of: c'}),
                ('repeat', {'a': a, 'b': b, 'c': bar_exp, 'd': bar_exp}),
                ('combine', {'a': a, 'b': b, '{c|d}': bar_exp}),
            ]
            for mode, param_help_map in cases:
                with self.subTest(bar_help=bar_help):
                    with self.assert_help_and_rst_match(mode, param_help_map, help_header, mode) as Foo:

                        class Bar(Foo, choices=choice_map, help=bar_help):
                            pass

    def test_subcommand_choices_map_custom_format(self):
        help_header = 'Subcommands:\n  {a|b|c|d}\n'
        a, b, c, bar = 'Find As', 'Find Bs', 'Find Cs', 'Execute bar'
        fmt_a, fmt_b = '{help} [Alias of: {choice}]', 'Test {alias}'
        cases = [
            (fmt_a, {'a': a, 'b': b, 'c': None, 'd': ''}, {'a': a, 'b': b, 'c': bar, 'd': f'{bar} [Alias of: c]'}),
            (fmt_a, {'a': a, 'b': b, 'c': c, 'd': c}, {'a': a, 'b': b, 'c': c, 'd': f'{c} [Alias of: c]'}),
            (fmt_b, {'a': a, 'b': b, 'c': c, 'd': c}, {'a': a, 'b': b, 'c': c, 'd': 'Test d'}),
        ]
        for fmt_str, choice_map, param_help_map in cases:
            with self.assert_help_and_rst_match('alias', param_help_map, help_header) as Foo:

                class Bar(Foo, choices=choice_map, help=bar, cmd_alias_mode=fmt_str):
                    pass


def get_expected_help_and_rst(help_header: str, param_help_map: Dict[str, str]) -> Tuple[str, str]:
    kf = '    {:s}\n'.format
    hf = '    {:<25s} {}\n'.format
    rf = '    |             |     {:<13s} |\n'.format
    expected_help = help_header + ''.join(hf(k, v) if v else kf(k) for k, v in param_help_map.items())
    table = RstTable.from_dict({f'``{k}``': v for k, v in param_help_map.items()}, use_table_directive=False)
    expected_rst = ''.join(rf(line) for line in table.iter_build() if line)
    return expected_help, expected_rst


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

        help_line = '  --help, -h                  Show this help message and exit (default: False)'
        expected_sub_cmd = 'Subcommands:\n  {show}\n    show                      Show the results of an action'
        verbose_desc = 'Increase logging verbosity (can specify multiple times) (default: 0)'

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
          --help, -h                  Show this help message and exit (default: False)

        Mutually exclusive options:
          --basic, -B                 Display colors without the 38;5; prefix (cannot be combined with other args) (default: False)
          --hex, -H                   Display colors by hex value (cannot be combined with other args) (default: False)
          --all, -A                   Show all foreground and background colors (only when no color/bg is specified) (default: False)

        Optional arguments:
          --color COLOR, -c COLOR     Text color to use (default: cycle through 0-256)
          --background BACKGROUND, -b BACKGROUND
                                      Background color to use (default: None)
        """
        expected = dedent(expected).lstrip()

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

        self.assert_strings_equal(expected, get_help_text(AnsiColorTest), diff_lines=7)

    def test_nested_show_tree(self):
        expected = """
        usage: foo.py [--foo FOO] [--arg_a ARG_A] [--arg_b ARG_B] [--arg_y ARG_Y] [--arg_z ARG_Z] [--bar] [--baz] [--help]

        Optional arguments:
        │ --foo FOO, -f FOO         Do foo
        │ --help, -h                Show this help message and exit (default: False)
        │
        Mutually exclusive options:
        ¦ --arg_a ARG_A, -a ARG_A   A
        ¦ --arg_b ARG_B, -b ARG_B   B
        ¦
        ¦ Mutually dependent options:
        ¦ ║ --arg_y ARG_Y, -y ARG_Y
        ¦ ║                         Y
        ¦ ║ --arg_z ARG_Z, -z ARG_Z
        ¦ ║                         Z
        ¦ ║
        ¦
        ¦ Optional arguments:
        ¦ │ --bar                   (default: False)
        ¦ │ --baz                   (default: False)
        ¦ │
        ¦
        """
        expected = dedent(expected).strip()

        class Foo(Command, show_group_tree=True, prog='foo.py'):
            foo = Option('-f', help='Do foo')
            with ParamGroup(mutually_exclusive=True):
                arg_a = Option('-a', help='A')
                arg_b = Option('-b', help='B')
                with ParamGroup(mutually_dependent=True):
                    arg_y = Option('-y', help='Y')
                    arg_z = Option('-z', help='Z')
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
            self.assertEqual([], get_usage_sub_cmds(Bar))

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


def _get_output(command: CommandCls, args: Sequence[str]) -> Tuple[str, str]:
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
