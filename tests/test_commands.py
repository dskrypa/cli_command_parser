#!/usr/bin/env python

import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import Command, Action, ActionFlag, SubCommand
from command_parser.exceptions import CommandDefinitionError
from command_parser.utils import Args


class TestCommands(TestCase):
    def test_true_on_action_handled(self):
        mock = Mock(__name__='foo')

        class Foo(Command):
            action = Action()
            action(mock)

        foo = Foo.parse(['foo'])
        self.assertFalse(mock.called)
        self.assertTrue(foo.main())
        self.assertTrue(mock.called)

    def test_true_on_action_flag_handled(self):
        mock = Mock()

        class Foo(Command):
            foo = ActionFlag()(mock)

        foo = Foo.parse(['--foo'])
        self.assertFalse(mock.called)
        self.assertTrue(foo.main())
        self.assertTrue(mock.called)

    def test_false_on_no_action(self):
        mock = Mock()

        class Foo(Command):
            foo = ActionFlag()(mock)

        foo = Foo.parse([])
        self.assertFalse(foo.main())
        self.assertFalse(mock.called)

    def test_parse_and_run(self):
        mock = Mock(__name__='bar')

        class Foo(Command):
            action = Action()
            action.register(mock)

        Foo.parse_and_run(['bar'])
        self.assertEqual(mock.call_count, 1)

    def test_cmd_in_sub_class_requires_sub_cmd_param(self):
        class Foo(Command):
            pass

        with self.assertRaises(CommandDefinitionError):

            class Bar(Foo, cmd='bar'):
                pass

    def test_multiple_actions_rejected(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                a = Action()
                b = Action()

    def test_multiple_sub_cmds_rejected(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                a = SubCommand()
                b = SubCommand()

    def test_action_with_sub_cmd_rejected(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                a = SubCommand()
                b = Action()

    def test_stdout_close(self):
        mock = Mock(close=Mock())
        with redirect_stdout(mock):
            Command(Args([])).run(close_stdout=True)

        self.assertTrue(mock.close.called)

    def test_stdout_close_error(self):
        mock = Mock(close=Mock(side_effect=ValueError))
        with redirect_stdout(mock):
            Command(Args([])).run(close_stdout=True)

        self.assertTrue(mock.close.called)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
