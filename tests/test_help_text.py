#!/usr/bin/env python

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock, patch, MagicMock

from command_parser import Command, no_exit_handler
from command_parser.commands import CommandType
from command_parser.parameters import Positional, SubCommand, Action, Counter, ParameterGroup
from command_parser.utils import ProgramMetadata

TEST_DESCRIPTION = 'This is a test description'
TEST_EPILOG = 'This is a test epilog'


class HelpTextTest(TestCase):
    def test_prog(self):
        class Foo(Command, error_handler=no_exit_handler, prog='foo.py'):
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
            foo = ParameterGroup(description='group foo')
            with ParameterGroup(description='test group') as group:
                bar = Positional()
                baz = Positional()

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertIn('test group:', stdout.splitlines())
        self.assertNotIn('group foo:', stdout)
        self.assertNotIn('Positional arguments:', stdout)

    def test_meta_init(self):
        g = {'__author_email__': 'example@fake.com', '__version__': '3.2.1', '__url__': 'https://github.com/foo/bar'}
        with (
            patch('command_parser.utils.getsourcefile', return_value='foo-script.py'),
            patch.object(ProgramMetadata, '_find_dunder_info', return_value=(True, g)),
            patch('command_parser.utils.sys.argv', ['bar.py']),
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
            patch('command_parser.utils.getsourcefile', return_value='foo-script.py'),
            patch('command_parser.utils.stack', return_value=[frame_info, frame_info]),
            patch('command_parser.utils.sys.argv', []),
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

    def test_empty_groups_hidden(self):
        class Base(Command):
            sub_cmd = SubCommand()
            verbose = Counter('-v', help='Increase logging verbosity (can specify multiple times)')

        class Show(Base, choice='show', help='Show the results of an action'):
            action = Action(help='What to show')
            action(Mock(__name__='attrs'))
            action(Mock(__name__='hello'))
            action(Mock(__name__='log_test'))

        help_text = Base.parser().formatter.format_help()
        self.assertNotIn('Positional arguments:', help_text)
        expected_sub_cmd = 'Subcommands:\n  {show}\n    show                      Show the results of an action'
        self.assertIn(expected_sub_cmd, help_text)
        expected_opt = """Optional arguments:
  --help, -h                  Show this help message and exit (default: False)
  --verbose [VERBOSE], -v [VERBOSE]
                              Increase logging verbosity (can specify multiple times) (default: 0)"""
        self.assertIn(expected_opt, help_text)


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
