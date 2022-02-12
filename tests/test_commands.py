#!/usr/bin/env python

from contextlib import redirect_stdout
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Action, ActionFlag, SubCommand, Positional
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

    def test_choice_in_sub_class_warns_on_no_sub_cmd_param(self):
        class Foo(Command):
            pass

        with self.assertWarnsRegex(Warning, expected_regex='has no SubCommand parameter'):

            class Bar(Foo, choice='bar'):
                pass

    def test_multiple_actions_rejected(self):
        class Foo(Command):
            a = Action()
            b = Action()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser()

    def test_multiple_sub_cmds_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser()

    def test_action_with_sub_cmd_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = Action()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser()

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

    def test_choice_with_no_parent_warns(self):
        with self.assertWarnsRegex(Warning, 'because it has no parent Command'):

            class Foo(Command, choice='foo'):
                pass

    def test_positional_after_sub_cmd_rejected(self):
        with self.assertRaises(CommandDefinitionError) as ctx:

            class Foo(Command):
                sub = SubCommand()
                pos = Positional()

            class Bar(Foo, choice='bar'):
                pass

        self.assertIn('may not follow the sub command', str(ctx.exception))

    def test_two_actions_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = Action()
            foo(Mock(__name__='baz'))

        with self.assertRaises(CommandDefinitionError) as ctx:
            Foo.parser()

        self.assertIn('Only 1 Action xor SubCommand is allowed', str(ctx.exception))

    def test_action_with_sub_command_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = SubCommand()
            foo(Mock(__name__='baz'))

        with self.assertRaises(CommandDefinitionError) as ctx:
            Foo.parser()

        self.assertIn('Only 1 Action xor SubCommand is allowed', str(ctx.exception))


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
