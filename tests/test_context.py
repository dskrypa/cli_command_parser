#!/usr/bin/env python

from unittest import TestCase, main

from cli_command_parser import Command, CommandConfig
from cli_command_parser.core import CommandMeta
from cli_command_parser.context import Context, get_current_context, ctx, get_context, get_parsed, ActionPhase
from cli_command_parser.error_handling import extended_error_handler
from cli_command_parser.parameters import Flag


class ContextTest(TestCase):
    def test_no_command_results_in_config_default(self):
        self.assertIs(CommandConfig().ignore_unknown, Context().config.ignore_unknown)

    def test_ctx_config_overrides_command(self):
        class Foo(Command):
            pass

        c = Context([], Foo, ignore_unknown=not CommandMeta.config(Foo).ignore_unknown)
        self.assertNotEqual(CommandMeta.config(Foo).ignore_unknown, c.config.ignore_unknown)

    def test_ctx_config_from_command(self):
        default = CommandConfig().ignore_unknown

        class Foo(Command, ignore_unknown=not default):
            pass

        c = Context([], Foo)
        self.assertNotEqual(default, c.config.ignore_unknown)

    def test_silent_no_current_context(self):
        self.assertIs(None, get_current_context(True))

    def test_error_on_no_current_context(self):
        with self.assertRaises(RuntimeError):
            get_current_context()

    def test_params_none_with_no_cmd(self):
        self.assertIs(None, Context().params)

    def test_empty_parsed_with_no_cmd(self):
        self.assertEqual({}, Context().get_parsed())

    def test_parsed_action_flags_with_no_cmd(self):
        expected = (0, [], [])
        self.assertEqual(expected, Context()._parsed_action_flags)

    def test_entered_context_is_active_context(self):
        with Context() as c1:
            self.assertEqual(c1, ctx)
            with ctx as c2:
                self.assertEqual(c2, ctx)
                self.assertEqual(c2, c1)

    def test_param_not_in_ctx(self):
        f = Flag()
        with Context():
            self.assertNotIn(f, ctx)

    def test_empty_parsed_always_available_action_flags(self):
        with Context() as c:
            self.assertEqual(0, len(c.categorized_action_flags[ActionPhase.PRE_INIT]))

    def test_double_config_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Cannot combine config='):
            Context(config=CommandConfig(), add_help=False)

    def test_explicitly_provided_config_used(self):
        config = CommandConfig()
        context = Context(config=config)
        self.assertIs(config, context.config)

    def test_config_as_dict(self):
        context = Context(config={'add_help': False})
        self.assertDictEqual({'add_help': False}, context.config.as_dict(False))

    def test_config_from_kwargs(self):
        context = Context(add_help=False)
        self.assertDictEqual({'add_help': False}, context.config.as_dict(False))

    def test_config_from_command(self):
        class Foo(Command, add_help=False):
            pass

        context = Context(command=Foo, show_docstring=False)
        self.assertDictEqual({'show_docstring': False}, context.config.as_dict(False))
        self.assertEqual(1, len(context.config.parents))
        self.assertFalse(context.config.add_help)
        self.assertFalse(context.config.show_docstring)

    def test_config_from_command_with_no_config(self):
        context = Context(command=Command, show_docstring=False)
        self.assertEqual(0, len(context.config.parents))
        self.assertFalse(context.config.show_docstring)

    def test_set_attr_thru_proxy(self):
        with Context() as outer_ctx:
            orig = ctx.argv
            with Context() as inner_ctx:
                ctx.argv = ['test', '123']

        self.assertEqual(['test', '123'], inner_ctx.argv)
        self.assertNotEqual(orig, inner_ctx.argv)
        self.assertEqual(orig, outer_ctx.argv)

    def test_default_error_handler_returned(self):
        self.assertIs(extended_error_handler, Context().get_error_handler())

    def test_get_context_bad(self):
        with self.assertRaises(TypeError):
            get_context(Command)  # noqa

    def test_get_context_ok(self):
        class Foo(Command):
            pass

        foo = Foo()
        self.assertIs(foo.ctx, get_context(foo))

    def test_get_parsed(self):
        class Foo(Command):
            a = Flag('-a')
            b = Flag('-b')

        foo = Foo.parse(['-ab'])
        self.assertDictEqual({'a': True, 'b': True, 'help': False}, get_parsed(foo))

        def bar(a):
            pass

        def baz(a, **kwargs):
            pass

        def zab(a, **b):
            pass

        self.assertDictEqual({'a': True}, get_parsed(foo, bar))
        self.assertDictEqual({'a': True}, get_parsed(foo, baz))
        self.assertDictEqual({'a': True}, get_parsed(foo, zab))

    def test_sub_context_terminal_width(self):
        with Context(terminal_width=30) as c1:
            c2 = c1._sub_context(None)  # noqa
            self.assertEqual(30, c2.terminal_width)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
