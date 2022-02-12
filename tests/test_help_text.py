#!/usr/bin/env python

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, no_exit_handler
from command_parser.commands import CommandType
from command_parser.parameters import Positional, SubCommand, Action, ActionFlag, Option, ParameterGroup, PassThru, Flag

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
        self.assertIn('Positional arguments:', stdout)
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
                bar = Flag()
                baz = Flag()

        stdout, stderr = _get_output(Foo, ['-h'])
        self.assertTrue(any(line == 'test group:' for line in stdout.splitlines()))
        self.assertNotIn('group foo:', stdout)
        self.assertNotIn('Positional arguments:', stdout)


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
