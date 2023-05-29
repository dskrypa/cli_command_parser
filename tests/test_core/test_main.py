#!/usr/bin/env python

from abc import ABC
from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, main as cmd_main, SubCommand
from cli_command_parser.core import CommandMeta
from cli_command_parser.testing import ParserTest


class MainTest(ParserTest):
    def setUp(self):
        CommandMeta._commands.clear()

    def test_main_calls_only_cmd(self):
        class Foo(Command):
            main = Mock()

        cmd_main([])
        self.assertTrue(Foo.main.called)

    def test_main_raises_error_on_0_cmds(self):
        with self.assert_raises_contains_str(RuntimeError, 'no commands were found'):
            cmd_main([])

    def test_main_raises_error_on_2_cmds(self):
        class Foo(Command):
            pass

        class Bar(Command):
            pass

        with self.assert_raises_contains_str(RuntimeError, 'found 2 commands:'):
            cmd_main([])

    def test_main_ignores_sub_cmd(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            parse_and_run = Mock()

        class Bar(Foo):
            parse_and_run = Mock()

        cmd_main([])
        self.assertTrue(Foo.parse_and_run.called)
        self.assertFalse(Bar.parse_and_run.called)

    def test_main_ignores_abc(self):
        class Foo(Command, ABC):
            pass

        class Bar(Foo):
            main = Mock()

        cmd_main([])
        self.assertTrue(Bar.main.called)

    def test_main_returns_none(self):
        class Foo(Command):
            pass

        self.assertIs(None, cmd_main([]))

    def test_main_returns_command(self):
        class Foo(Command):
            pass

        self.assertIsInstance(cmd_main([], return_command=True), Foo)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
