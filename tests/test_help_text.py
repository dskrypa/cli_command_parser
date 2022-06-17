#!/usr/bin/env python

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Sequence, Type, Union, Iterable, Any, Tuple
from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser import Command, no_exit_handler, Context, ShowDefaults
from cli_command_parser.core import get_params, CommandType
from cli_command_parser.exceptions import MissingArgument
from cli_command_parser.formatting.params import ParamHelpFormatter, PositionalHelpFormatter
from cli_command_parser.formatting.utils import get_usage_sub_cmds
from cli_command_parser.parameters.choice_map import ChoiceMap, SubCommand, Action
from cli_command_parser.parameters import Positional, Counter, ParamGroup, Option, Flag, PassThru, action_flag
from cli_command_parser.testing import ParserTest
from cli_command_parser.utils import ProgramMetadata, ProgInfo

TEST_DESCRIPTION = 'This is a test description'
TEST_EPILOG = 'This is a test epilog'


class HelpTextTest(TestCase):
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

    def test_pass_thru_usage(self):
        class Foo(Command):
            foo = Option()
            bar = PassThru()

        help_text = _get_help_text(Foo)
        self.assertIn('--foo', help_text)
        self.assertIn('[-- BAR]', help_text)

    def test_custom_choice_map(self):
        class Custom(ChoiceMap):
            pass

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
  --format {json,json-pretty,json-compact,text,yaml,pprint,csv,table,pseudo-yaml,json-lines,plain,pseudo-json}, -f {json,json-pretty,json-compact,text,yaml,pprint,csv,table,pseudo-yaml,json-
                              lines,plain,pseudo-json}
                              Output format to use for --full_info (default: 'yaml')
  --test TEST, -t TEST        0 extra long help text example,1 extra long help text example,2 extra long help text example,3 extra long help text example,4 extra long help text example,5 extra long
                              help text example,6 extra long help text example,7 extra long help text example,8 extra long help text example,9 extra long help text example"""

        help_text = _get_help_text(Base.parse(['find', '-h']))
        self.assertIn(expected, help_text)

    def test_subcommand_is_in_usage(self):
        class Foo(Command, prog='foo.py'):
            sub_cmd = SubCommand()

        class Bar(Foo):
            pass

        class Baz(Foo):
            pass

        usage = _get_usage_text(Baz)
        self.assertEqual('usage: foo.py baz [--help]', usage)

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
            usage: foo.py {bar,baz} [--abc] [--help]

            Subcommands:
              {bar,baz}
                bar
                baz

            Optional arguments:
              --abc                       (default: False)
              --help, -h                  Show this help message and exit (default: False)
            """
        ).lstrip()
        help_text = _get_help_text(Foo)
        self.assertEqual(expected, help_text)

    def test_usage_lambda_type(self):
        class Foo(Command, use_type_metavar=True):
            bar = Option(type=lambda v: v * 2)
            baz = Option(type=int)

        usage_text = _get_usage_text(Foo)
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

        usage_text = _get_usage_text(Foo)
        self.assertIn('--bar BAR', usage_text)
        self.assertIn('--baz INT', usage_text)

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

    # TODO:BUG?: Fix handling of -fh / -hf
    def test_help_called_with_unrecognized_args(self):
        when_cases_map = {
            # 'before': (['--foo', '-h'], ['-fh'], ['-f', '1', '-h'], ['f', '--help']),
            # 'after': (['-h', '--foo'], ['-hf'], ['-h', '-f', '1'], ['--help', 'f']),
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

    def test_underscore_and_dash_enabled(self):
        class Foo(Command, option_name_mode='both'):
            foo_bar = Flag()

        help_text = _get_help_text(Foo)
        self.assertIn('--foo-bar', help_text)
        self.assertIn('--foo_bar', help_text)

    def test_only_dash_enabled(self):
        class Foo(Command, option_name_mode='dash'):
            foo_bar = Flag()

        help_text = _get_help_text(Foo)
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

                help_text = _get_help_text(Foo)
                self.assertTrue(all(exp in help_text for exp in base_expected))
                self.assertTrue(all(exp in help_text for exp in expected_a))
                self.assertNotIn('--foo_e', help_text)
                self.assertNotIn('--foo-e', help_text)


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
                Base.config().use_type_metavar = use_type_metavar

                help_text = _get_help_text(Base)
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

        help_text = _get_help_text(Foo)
        rst_test = _get_rst_text(Foo)
        self.assertIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)
        self.assertNotIn('--baz', rst_test)

    def test_hidden_groups_not_shown(self):
        class Foo(Command):
            foo = Option()
            with ParamGroup(hide=True) as outer:
                bar = Option()
                with ParamGroup() as inner:
                    baz = Flag()

        help_text = _get_help_text(Foo)
        self.assertIn('--foo', help_text)
        self.assertNotIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)

    def test_anon_group_auto_names_not_used(self):
        expected = """
        usage: ansi_color_test.py [--text TEXT] [--attr {bold,dim}] [--limit LIMIT] [--basic] [--hex] [--all] [--color COLOR] [--background BACKGROUND] [--help]

        Tool for testing ANSI colors

        Optional arguments:
          --text TEXT, -t TEXT        Text to be displayed (default: the number of the color being shown)
          --attr {bold,dim}, -a {bold,dim}
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

        self.assert_strings_equal(expected, _get_help_text(AnsiColorTest), diff_lines=7)

    def test_nested_show_tree(self):
        expected = """
        usage: foo.py [--foo FOO] [--arg_a ARG_A] [--arg_b ARG_B] [--arg_y ARG_Y] [--arg_z ARG_Z] [--bar] [--baz] [--help]

        Optional arguments:
        │   --foo FOO, -f FOO         Do foo
        │   --help, -h                Show this help message and exit (default: False)
        │
        Mutually exclusive options:
        ¦   --arg_a ARG_A, -a ARG_A   A
        ¦   --arg_b ARG_B, -b ARG_B   B
        ¦
        ¦ Mutually dependent options:
        ¦ ║   --arg_y ARG_Y, -y ARG_Y Y
        ¦ ║   --arg_z ARG_Z, -z ARG_Z Z
        ¦ ║
        ¦
        ¦ Optional arguments:
        ¦ │   --bar                   (default: False)
        ¦ │   --baz                   (default: False)
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

        help_text = _get_help_text(Foo).rstrip()
        self.assert_strings_equal(expected, help_text, diff_lines=7, trim=True)


def _get_usage_text(cmd: Type[Command]) -> str:
    with cmd().ctx:
        return get_params(cmd).formatter.format_usage()


def _get_help_text(cmd: Union[Type[Command], Command]) -> str:
    if not isinstance(cmd, Command):
        cmd = cmd()
    with patch('cli_command_parser.formatting.utils.get_terminal_size', return_value=(199, 1)):
        with cmd.ctx:
            return get_params(cmd).formatter.format_help()


def _get_rst_text(cmd: Union[Type[Command], Command]) -> str:
    if not isinstance(cmd, Command):
        cmd = cmd()
    with patch('cli_command_parser.formatting.utils.get_terminal_size', return_value=(199, 1)):
        with cmd.ctx:
            return get_params(cmd).formatter.format_rst()


class ProgramMetadataTest(TestCase):
    def test_meta_init(self):
        g = {
            '__package__': 'bar.cli',
            '__author_email__': 'example@fake.com',
            '__version__': '3.2.1',
            '__url__': 'https://github.com/foo/bar',
        }
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('bar.py')
            tmp_path.touch()
            with patch('cli_command_parser.utils.sys.argv', [tmp_path.as_posix()]):
                with patch('cli_command_parser.utils.stack', return_value=_mock_stack(g)):
                    meta = ProgramMetadata()
                    self.assertEqual(meta.path.name, 'bar.py')
                    self.assertEqual(meta.prog, 'bar.py')
                    self.assertEqual(meta.docs_url, 'https://foo.github.io/bar/')
                    self.assertEqual(meta.url, g['__url__'])
                    self.assertEqual(meta.email, g['__author_email__'])
                    self.assertEqual(meta.version, g['__version__'])

    def test_extended_epilog(self):
        meta = ProgramMetadata(
            prog='foo', epilog='test', version='4.3.2', email='example@fake.com', url='http://fake.com'
        )
        self.assertEqual(meta.format_epilog(False), 'test')
        expected = 'test\n\nReport foo [ver. 4.3.2] bugs to example@fake.com\n\nOnline documentation: http://fake.com'
        self.assertEqual(meta.format_epilog(), expected)

    def test_extended_epilog_no_email(self):
        meta = ProgramMetadata(prog='foo', epilog='test', version='4.3.2', url='http://fake.com')
        self.assertEqual(meta.format_epilog(), 'test\n\nOnline documentation: http://fake.com')

    def test_doc_url_none(self):
        meta = ProgramMetadata(url='https://github.com/foo')
        self.assertIs(meta.docs_url, None)

    @patch('cli_command_parser.utils.sys.argv', [])
    def test_find_dunder_info(self, *mocks):
        g = {
            '__package__': 'foo.cli',
            '__author_email__': 'example@fake.com',
            '__version__': '3.2.1',
            '__url__': 'https://github.com/foo/bar',
        }
        with patch('cli_command_parser.utils.stack', return_value=_mock_stack(g)):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'foo.py')
            self.assertEqual(meta.prog, 'foo.py')
            self.assertEqual(meta.docs_url, 'https://foo.github.io/bar/')
            self.assertEqual(meta.url, g['__url__'])
            self.assertEqual(meta.email, g['__author_email__'])
            self.assertEqual(meta.version, g['__version__'])

    @patch('cli_command_parser.utils.sys.argv', [])
    def test_prog_info_no_external_pkg(self, *mocks):
        g = {'__package__': 'cli_command_parser'}
        with patch('cli_command_parser.utils.stack', return_value=_mock_stack(g)):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'foo.py')
            self.assertEqual(meta.prog, 'foo.py')

    @patch('cli_command_parser.utils.sys.argv', [])
    def test_resolve_path_no_setup_no_argv(self, *mocks):
        with patch.object(ProgInfo, '_find_top_frame_and_globals', side_effect=RuntimeError):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'UNKNOWN')
            self.assertEqual(meta.prog, 'UNKNOWN')

    @patch('cli_command_parser.utils.sys.argv', ['fake\n\nfile!'])
    def test_find_info_error(self, *mocks):
        with patch.object(ProgInfo, '_find_top_frame_and_globals', side_effect=RuntimeError):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'UNKNOWN')
            self.assertIs(meta.docs_url, None)
            self.assertIs(meta.url, None)
            self.assertIs(meta.email, None)
            self.assertEqual(meta.version, '')

    def test_print_stack_info(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            ProgInfo._print_stack_info()
        self.assertLess(1, stdout.getvalue().count('\n'))

    def test_empty_doc_ignored(self):
        meta = ProgramMetadata(doc='\n\n')
        self.assertIs(None, meta.description)

    def test_cmd_doc_dedented(self):
        class Foo(Command):
            """
            Foo
            Bar
            Baz
            """

        self.assertEqual('Foo\nBar\nBaz\n', Foo.meta().description)


def _frame_info(f_globals: dict, path: str, function: str):
    return Mock(frame=Mock(f_globals=f_globals), filename=path, function=function)


def _mock_stack(g: dict, file_name: str = 'foo.py', setup: bool = True, main_fn: bool = False, top_name: str = None):
    pkg_g = {'__package__': 'cli_command_parser'}
    root = '/home/user/git/foo_proj/'
    pkg_path = f'{root}venv/lib/site-packages/cli_command_parser/'
    cmds_path = f'{pkg_path}commands.py'

    cmd_mid_stack = [_frame_info(pkg_g, cmds_path, '__call__'), _frame_info(pkg_g, cmds_path, 'parse_and_run')]
    if main_fn:
        cmd_mid_stack.append(_frame_info(pkg_g, cmds_path, 'main'))

    if setup:
        if top_name is None:
            name, ext = file_name.rsplit('.', 1)
            top_name = f'{name}-script.{ext}'
        top_path, end_path = f'{root}venv/bin/{top_name}', f'{root}lib/cli/{file_name}'
        top_g = {'__package__': None, 'load_entry_point': 1}
    else:
        top_path = end_path = f'{root}bin/{file_name}'
        top_g = g

    return [
        _frame_info(pkg_g, f'{pkg_path}utils.py', '_find_top_frame_and_globals'),
        _frame_info(g, end_path, 'main'),
        *cmd_mid_stack,
        _frame_info(top_g, top_path, '<module>'),
    ]


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


def _get_output(command: CommandType, args: Sequence[str]) -> Tuple[str, str]:
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        command.parse_and_run(args)

    return stdout.getvalue(), stderr.getvalue()


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
