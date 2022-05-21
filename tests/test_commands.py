#!/usr/bin/env python

from abc import ABC
from contextlib import redirect_stdout, redirect_stderr
from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command, CommandConfig, Context
from cli_command_parser.core import get_config, get_parent, get_params
from cli_command_parser.error_handling import no_exit_handler, extended_error_handler
from cli_command_parser.exceptions import CommandDefinitionError, NoSuchOption
from cli_command_parser.parameters import Action, ActionFlag, SubCommand, Positional, Flag


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
        self.assertEqual(0, foo.ctx.actions_taken)
        self.assertEqual(1, foo())
        self.assertEqual(1, foo.ctx.actions_taken)
        self.assertTrue(mock.called)

    def test_false_on_no_action(self):
        mock = Mock()

        class Foo(Command):
            foo = ActionFlag()(mock)

        foo = Foo.parse([])
        with foo.ctx:
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
            Foo.parse([])

    def test_multiple_sub_cmds_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    def test_action_with_sub_cmd_rejected(self):
        class Foo(Command):
            a = SubCommand()
            b = Action()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

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
            Foo.parse([])

    def test_action_with_sub_command_rejected(self):
        class Foo(Command):
            foo = Action()
            bar = SubCommand()
            foo(Mock(__name__='baz'))

        with self.assertRaisesRegex(CommandDefinitionError, 'Only 1 Action xor SubCommand is allowed'):
            Foo.parse([])

    def test_no_error_handler_run(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            __call__ = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.__call__.called)

    def test_no_error_handler_main(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            main = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.main.called)

    def test_no_run_after_parse_error(self):
        class Foo(Command, error_handler=no_exit_handler):
            bar = Flag()
            __call__ = Mock()

        mock = Mock(close=Mock())
        with redirect_stdout(mock), redirect_stderr(mock):
            Foo.parse_and_run(['-B'])

        self.assertFalse(Foo.__call__.called)

    def test_no_warn_on_parent_without_choice(self):
        class Foo(Command):
            pass

        class Bar(Foo):
            pass

        self.assertEqual(get_params(Bar).command_parent, Foo)

    def test_double_config_rejected(self):
        with self.assertRaisesRegex(CommandDefinitionError, 'Cannot combine .* with keyword config'):

            class Foo(Command, config=CommandConfig(), multiple_action_flags=True):
                pass

    def test_config_defaults(self):
        class Foo(Command):
            pass

        config = Foo.config()
        self.assertDictEqual(config.as_dict(), CommandConfig().as_dict())

    def test_config_from_kwarg(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, multiple_action_flags=not default):
            pass

        self.assertEqual(Foo.config().multiple_action_flags, not default)

    def test_config_explicit(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config=CommandConfig(multiple_action_flags=not default)):
            pass

        self.assertEqual(Foo.config().multiple_action_flags, not default)

    def test_config_inherited(self):
        default_config = CommandConfig()

        class Foo(Command, multiple_action_flags=not default_config.multiple_action_flags):
            pass

        self.assertEqual(Foo.config().action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Foo.config().multiple_action_flags, default_config.multiple_action_flags)

        class Bar(Foo, action_after_action_flags=not default_config.action_after_action_flags):
            pass

        self.assertNotEqual(Bar.config().action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Bar.config().multiple_action_flags, default_config.multiple_action_flags)
        # Ensure Foo config has not changed:
        self.assertEqual(Foo.config().action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(Foo.config().multiple_action_flags, default_config.multiple_action_flags)

    def test_default_error_handler_returned(self):
        self.assertIs(extended_error_handler, Context().get_error_handler())

    def test_no_help(self):
        class Foo(Command, add_help=False, error_handler=None):
            pass

        with self.assertRaises(NoSuchOption):
            Foo.parse_and_run(['-h'])

    def test_sub_command_adds_help(self):
        class Foo(Command, ABC):
            pass

        class Bar(Foo):
            pass

        with redirect_stdout(Mock()), self.assertRaises(SystemExit):
            Bar.parse_and_run(['-h'])

    def test_argv_results_in_sub_context(self):
        class Foo(Command):
            pass

        for context in (Context(['a'], Foo, ignore_unknown=True), Context(['a'], ignore_unknown=True)):
            with context as ctx:
                foo = Foo.parse_and_run(['b'])
                self.assertIs(ctx, foo.ctx.parent)
                self.assertListEqual(['a'], ctx.argv)
                self.assertListEqual(['b'], foo.ctx.argv)

    def test_no_argv_results_in_keeping_context(self):
        class Foo(Command):
            pass

        with Context(['a'], Foo, ignore_unknown=True) as ctx:
            foo = Foo.parse_and_run()
            self.assertIs(ctx, foo.ctx)
            self.assertListEqual(['a'], ctx.argv)
            self.assertListEqual(['a'], foo.ctx.argv)

    def test_no_argv_no_cmd_resuls_in_sub_context(self):
        class Foo(Command):
            pass

        with Context(['a'], ignore_unknown=True) as ctx:
            foo = Foo.parse_and_run()
            self.assertIs(ctx, foo.ctx.parent)
            self.assertListEqual(['a'], ctx.argv)
            self.assertListEqual(['a'], foo.ctx.argv)

    def test_get_config(self):
        cfg = CommandConfig()

        class Foo(Command, config=cfg):
            pass

        self.assertIs(cfg, get_config(Foo))
        self.assertIs(cfg, get_config(Foo()))

    def test_get_parent(self):
        class Foo(Command):
            pass

        self.assertIs(Command, get_parent(Foo))
        self.assertIs(Command, get_parent(Foo()))

    def test_multiple_non_required_positionals_rejected(self):
        for a, b in (('?', '?'), ('?', '*'), ('*', '?'), ('*', '*')):
            with self.subTest(a=a, b=b):

                class Foo(Command):
                    foo = Positional(nargs=a)
                    bar = Positional(nargs=b)

                with self.assertRaises(CommandDefinitionError):
                    Foo.params()

    def test_after_main_not_called_after_exc(self):
        class Foo(Command):
            _after_main_ = Mock()

            def main(self):
                raise RuntimeError('test')

        with self.assertRaisesRegex(RuntimeError, 'test'):
            Foo.parse_and_run([])

        self.assertFalse(Foo._after_main_.called)

    def test_after_main_called_after_exc(self):
        class Foo(Command, always_run_after_main=True):
            _after_main_ = Mock()

            def main(self):
                raise RuntimeError('test')

        with self.assertRaisesRegex(RuntimeError, 'test'):
            Foo.parse_and_run([])

        self.assertTrue(Foo._after_main_.called)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
