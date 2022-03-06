#!/usr/bin/env python

from unittest import TestCase, main

from cli_command_parser import Command
from cli_command_parser.config import CommandConfig
from cli_command_parser.context import Context, ConfigOption, get_current_context, ctx


class ContextTest(TestCase):
    def test_config_option_returns_self(self):
        self.assertIsInstance(Context.ignore_unknown, ConfigOption)

    def test_no_command_results_in_none(self):
        self.assertIs(None, Context().ignore_unknown)

    def test_ctx_config_overrides_command(self):
        class Foo(Command):
            pass

        c = Context([], Foo, ignore_unknown=not Foo.config().ignore_unknown)
        self.assertNotEqual(Foo.config().ignore_unknown, c.ignore_unknown)

    def test_ctx_config_from_command(self):
        default = CommandConfig().ignore_unknown

        class Foo(Command, ignore_unknown=not default):
            pass

        c = Context([], Foo)
        self.assertNotEqual(default, c.ignore_unknown)

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
        self.assertEqual(expected, Context().parsed_action_flags)

    def test_entered_context_is_active_context(self):
        with Context() as c1:
            self.assertEqual(c1, ctx)
            with ctx as c2:
                self.assertEqual(c2, ctx)
                self.assertEqual(c2, c1)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
