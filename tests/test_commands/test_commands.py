#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, Context
from cli_command_parser.exceptions import ParamConflict
from cli_command_parser.parameters import Action, ActionFlag
from cli_command_parser.testing import ParserTest, sealed_mock


class TestCommands(ParserTest):
    def test_true_on_action_handled(self):
        mock = sealed_mock(__name__='foo')

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
        mock = sealed_mock(__name__='bar')

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

        with self.assert_raises_contains_str(RuntimeError, 'test'):
            Foo.parse_and_run([])

        self.assertFalse(Foo._after_main_.called)

    def test_after_main_called_after_exc(self):
        class Foo(Command, always_run_after_main=True):
            _after_main_ = Mock()

            def main(self):
                raise RuntimeError('test')

        with self.assert_raises_contains_str(RuntimeError, 'test'):
            Foo.parse_and_run([])

        self.assertTrue(Foo._after_main_.called)

    def test_action_after_action_flags_exc(self):
        act_flag_mock = Mock()
        action_mock = sealed_mock(__name__='b')

        class Foo(Command, action_after_action_flags=False, error_handler=None):
            a = ActionFlag('-a')(act_flag_mock)
            c = Action()
            c(action_mock)

        with self.assert_raises_contains_str(ParamConflict, 'combining an action with action flags is disabled'):
            Foo.parse_and_run(['b', '-a'])

        self.assertFalse(act_flag_mock.called)
        self.assertFalse(action_mock.called)

    def test_action_after_action_flags_ok(self):
        act_flag_mock = Mock()
        action_mock = sealed_mock(__name__='b')

        class Foo(Command):
            a = ActionFlag('-a')(act_flag_mock)
            c = Action()
            c(action_mock)

        Foo.parse_and_run(['b', '-a'])
        self.assertTrue(act_flag_mock.called)
        self.assertTrue(action_mock.called)

    def test_ctx_attr_retained(self):
        class Foo(Command):
            ctx = 123

        self.assertEqual(123, Foo().ctx)
        del Foo.ctx
        self.assertIsInstance(Foo().ctx, Context)

    def test_prog_in_repr(self):
        class Foo(Command, prog='foo.py'):
            pass

        self.assertEqual("<Foo in prog='foo.py'>", repr(Foo()))


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
