#!/usr/bin/env python

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Action, ActionFlag, SubCommand, Positional, Flag, Option, CommandConfig, BaseCommand
from command_parser.exceptions import CommandDefinitionError
from command_parser.utils import Args
from command_parser.error_handling import no_exit_handler, error_handler


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

    def test_actions_taken_incremented_on_action_flag_handled(self):
        mock = Mock()

        class Foo(Command):
            foo = ActionFlag()(mock)

        foo = Foo.parse(['--foo'])
        self.assertFalse(mock.called)
        self.assertEqual(0, foo.args.actions_taken)
        self.assertEqual(1, foo.run())
        self.assertEqual(1, foo.args.actions_taken)
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
            Foo.parser  # noqa

    def test_multiple_sub_cmds_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser  # noqa

    def test_action_with_sub_cmd_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = Action()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser  # noqa

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
        with self.assertRaisesRegex(CommandDefinitionError, 'may not follow the sub command'):

            class Foo(Command):
                sub = SubCommand()
                pos = Positional()

            class Bar(Foo, choice='bar'):
                pass

    def test_two_actions_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = Action()
            foo(Mock(__name__='baz'))

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parser  # noqa

    def test_action_with_sub_command_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = SubCommand()
            foo(Mock(__name__='baz'))

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parser  # noqa

    def test_no_error_handler_run(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            run = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.run.called)

    def test_no_error_handler_main(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            main = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.main.called)

    def test_no_run_after_parse_error(self):
        class Foo(Command, error_handler=no_exit_handler):
            bar = Flag()
            run = Mock()

        mock = Mock(close=Mock())
        with redirect_stdout(mock), redirect_stderr(mock):
            Foo.parse_and_run(['-B'])

        self.assertFalse(Foo.run.called)

    def test_no_warn_on_parent_without_choice(self):
        class Foo(Command):
            pass

        class Bar(Foo):
            pass

        self.assertEqual(Bar.parser.command_parent, Foo)

    def test_double_config_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'Cannot combine .* with keyword config'):

            class Foo(Command, config=CommandConfig(), multiple_action_flags=True):
                pass

    def test_config_defaults(self):
        class Foo(Command):
            pass

        config = Foo.command_config
        self.assertDictEqual(asdict(config), asdict(CommandConfig()))

    def test_config_from_kwarg(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, multiple_action_flags=not default):
            pass

        self.assertEqual(Foo.command_config.multiple_action_flags, not default)

    def test_config_explicit(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config=CommandConfig(multiple_action_flags=not default)):
            pass

        self.assertEqual(Foo.command_config.multiple_action_flags, not default)

    def test_config_inherited(self):
        default_config = CommandConfig()

        class Foo(Command, multiple_action_flags=not default_config.multiple_action_flags):
            pass

        self.assertEqual(Foo.command_config.action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Foo.command_config.multiple_action_flags, default_config.multiple_action_flags)

        class Bar(Foo, action_after_action_flags=not default_config.action_after_action_flags):
            pass

        self.assertNotEqual(Bar.command_config.action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Bar.command_config.multiple_action_flags, default_config.multiple_action_flags)
        # Ensure Foo config has not changed:
        self.assertEqual(Foo.command_config.action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Foo.command_config.multiple_action_flags, default_config.multiple_action_flags)

    def test_default_error_handler_returned(self):
        self.assertIs(error_handler, BaseCommand._BaseCommand__get_error_handler())  # noqa


class TestParsing(TestCase):
    def test_flag_and_option(self):
        class Ipython(Command):
            interactive = Flag('-i')
            module = Option('-m')

        for case in (['-im', 'lib.command_parser'], ['-i', '-m', 'lib.command_parser']):
            with self.subTest(case=case):
                cmd = Ipython.parse(case)
                self.assertTrue(cmd.interactive)
                self.assertEqual(cmd.module, 'lib.command_parser')


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
