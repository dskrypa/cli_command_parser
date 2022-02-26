#!/usr/bin/env python

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock, patch, MagicMock

from cli_command_parser import Command, no_exit_handler
from cli_command_parser.commands import CommandType
from cli_command_parser.parameters import (
    Positional,
    SubCommand,
    Action,
    Counter,
    ParamGroup,
    Option,
    Flag,
    PassThru,
    ChoiceMap,
)
from cli_command_parser.utils import ProgramMetadata

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

        with patch('cli_command_parser.formatting.get_terminal_size', return_value=(199, 1)):
            help_text = Base.params.formatter.format_help()
        self.assertNotIn('Positional arguments:', help_text)
        expected_sub_cmd = 'Subcommands:\n  {show}\n    show                      Show the results of an action'
        self.assertIn(expected_sub_cmd, help_text)

        help_text_lines = help_text.splitlines()
        optional_header_index = help_text_lines.index('Optional arguments:')
        help_line = '  --help, -h                  Show this help message and exit (default: False)'
        self.assertIn(help_line, help_text_lines[optional_header_index:])
        verbose_line_1 = '  --verbose [VERBOSE], -v [VERBOSE]'
        verbose_line_2 = (' ' * 30) + 'Increase logging verbosity (can specify multiple times) (default: 0)'
        verbose_line_1_index = help_text_lines.index(verbose_line_1)
        self.assertGreater(verbose_line_1_index, optional_header_index)
        self.assertIn(verbose_line_2, help_text_lines[verbose_line_1_index:])

    def test_hidden_params_not_shown(self):
        class Foo(Command):
            bar = Option()
            baz = Flag(hide=True)

        self.assertFalse(Foo.bar.hide)
        self.assertTrue(Foo.baz.hide)
        self.assertTrue(Foo.bar.show_in_help)
        self.assertFalse(Foo.baz.show_in_help)

        help_text = Foo.params.formatter.format_help()
        self.assertIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)

    def test_hidden_groups_not_shown(self):
        class Foo(Command):
            foo = Option()
            with ParamGroup(hide=True) as outer:
                bar = Option()
                with ParamGroup() as inner:
                    baz = Flag()

        help_text = Foo.params.formatter.format_help()
        self.assertIn('--foo', help_text)
        self.assertNotIn('--bar', help_text)
        self.assertNotIn('--baz', help_text)

    def test_pass_thru_usage(self):
        class Foo(Command):
            foo = Option()
            bar = PassThru()

        help_text = Foo.params.formatter.format_help()
        self.assertIn('--foo', help_text)
        self.assertIn('[-- BAR]', help_text)

    def test_custom_choice_map(self):
        class Custom(ChoiceMap):
            pass

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
  --escape ESCAPE, -e ESCAPE  Escape the provided regex special characters (default: ())
  --allow_inst, -I            Allow search results that include instrumental versions of songs (default: False)
  --full_info, -F             Print all available info about the discovered objects (default: False)
  --format {json,json-pretty,json-compact,text,yaml,pprint,csv,table,pseudo-yaml,json-lines,plain,pseudo-json}, -f {json,json-pretty,json-compact,text,yaml,pprint,csv,table,pseudo-yaml,json-
                              lines,plain,pseudo-json}
                              Output format to use for --full_info (default: yaml)
  --test TEST, -t TEST        0 extra long help text example,1 extra long help text example,2 extra long help text example,3 extra long help text example,4 extra long help text example,5 extra long
                              help text example,6 extra long help text example,7 extra long help text example,8 extra long help text example,9 extra long help text example (default: None)"""

        with patch('cli_command_parser.formatting.get_terminal_size', return_value=(199, 1)):
            self.assertIn(expected, Base.parse(['find', '-h']).params.formatter.format_help())
        # Base.parse_and_run(['find', '-h'])


class ProgramMetadataTest(TestCase):
    def test_meta_init(self):
        g = {'__author_email__': 'example@fake.com', '__version__': '3.2.1', '__url__': 'https://github.com/foo/bar'}
        with (
            patch('cli_command_parser.utils.getsourcefile', return_value='foo-script.py'),
            patch.object(ProgramMetadata, '_find_dunder_info', return_value=(True, g)),
            patch('cli_command_parser.utils.sys.argv', ['bar.py']),
        ):
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

    def test_find_dunder_info(self):
        g = {
            '__author_email__': 'example@fake.com',
            '__version__': '3.2.1',
            '__url__': 'https://github.com/foo/bar',
            'load_entry_point': Mock(),
        }
        frame_info = MagicMock(frame=Mock(f_globals=g))
        with (
            patch('cli_command_parser.utils.getsourcefile', return_value='foo-script.py'),
            patch('cli_command_parser.utils.stack', return_value=[frame_info, frame_info]),
            patch('cli_command_parser.utils.sys.argv', []),
        ):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'foo.py')
            self.assertEqual(meta.prog, 'foo.py')
            self.assertEqual(meta.docs_url, 'https://foo.github.io/bar/')
            self.assertEqual(meta.url, g['__url__'])
            self.assertEqual(meta.email, g['__author_email__'])
            self.assertEqual(meta.version, g['__version__'])

    def test_find_info_error(self):
        with patch.object(ProgramMetadata, '_find_info', side_effect=RuntimeError):
            meta = ProgramMetadata()
            self.assertEqual(meta.path.name, 'utils.py')
            self.assertIs(meta.docs_url, None)
            self.assertIs(meta.url, None)
            self.assertIs(meta.email, None)
            self.assertEqual(meta.version, '')


def _get_output(command: CommandType, args: list[str]) -> tuple[str, str]:
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
