#!/usr/bin/env python

from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command, CommandConfig, Context
from cli_command_parser.core import CommandMeta, get_config, get_parent, get_params
from cli_command_parser.error_handling import no_exit_handler
from cli_command_parser.exceptions import CommandDefinitionError, ParamConflict
from cli_command_parser.parameters import Action, ActionFlag, Flag
from cli_command_parser.testing import RedirectStreams

_get_config = CommandMeta.config


class TestCommandMeta(TestCase):
    def test_choice_with_no_sub_cmd_param_warns(self):
        class Foo(Command):
            pass

        for kwargs in ({'choice': 'bar'}, {'choice': 'bar', 'choices': ('bar1',)}, {'choices': ('bar', 'bar1')}):
            with self.subTest(kwargs=kwargs), self.assertWarnsRegex(Warning, 'has no SubCommand parameter'):

                class Bar(Foo, **kwargs):
                    pass

    def test_choice_with_no_parent_warns(self):
        for kwargs in ({'choice': 'foo'}, {'choice': 'foo', 'choices': ('foo1',)}, {'choices': ('foo', 'foo1')}):
            with self.subTest(kwargs=kwargs), self.assertWarnsRegex(Warning, 'because it has no parent Command'):

                class Foo(Command, **kwargs):
                    pass

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

        config = _get_config(Foo)
        self.assertDictEqual(config.as_dict(), CommandConfig().as_dict())

    def test_config_from_kwarg(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, multiple_action_flags=not default):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_from_dict(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config={'multiple_action_flags': not default}):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_explicit(self):
        default = CommandConfig().multiple_action_flags

        class Foo(Command, config=CommandConfig(multiple_action_flags=not default)):
            pass

        self.assertEqual(_get_config(Foo).multiple_action_flags, not default)

    def test_config_inherited(self):
        default_config = CommandConfig()

        class Foo(Command, multiple_action_flags=not default_config.multiple_action_flags):
            pass

        self.assertEqual(_get_config(Foo).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Foo).multiple_action_flags, default_config.multiple_action_flags)

        class Bar(Foo, action_after_action_flags=not default_config.action_after_action_flags):
            pass

        self.assertNotEqual(_get_config(Bar).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Bar).multiple_action_flags, default_config.multiple_action_flags)
        # Ensure Foo config has not changed:
        self.assertEqual(_get_config(Foo).action_after_action_flags, default_config.action_after_action_flags)
        self.assertNotEqual(_get_config(Foo).multiple_action_flags, default_config.multiple_action_flags)

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


class TestErrorHandling(TestCase):
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

        with RedirectStreams():
            Foo.parse_and_run(['-B'])

        self.assertFalse(Foo.__call__.called)


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

    def test_action_after_action_flags_exc(self):
        act_flag_mock = Mock()
        action_mock = Mock(__name__='b')

        class Foo(Command, action_after_action_flags=False, error_handler=None):
            a = ActionFlag('-a')(act_flag_mock)
            c = Action()
            c(action_mock)

        with self.assertRaisesRegex(ParamConflict, 'combining an action with action flags is disabled'):
            Foo.parse_and_run(['b', '-a'])

        self.assertFalse(act_flag_mock.called)
        self.assertFalse(action_mock.called)

    def test_action_after_action_flags_ok(self):
        act_flag_mock = Mock()
        action_mock = Mock(__name__='b')

        class Foo(Command):
            a = ActionFlag('-a')(act_flag_mock)
            c = Action()
            c(action_mock)

        Foo.parse_and_run(['b', '-a'])
        self.assertTrue(act_flag_mock.called)
        self.assertTrue(action_mock.called)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
