#!/usr/bin/env python

import logging
from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command, Action, Positional
from cli_command_parser.exceptions import (
    ParameterDefinitionError,
    CommandDefinitionError,
    MissingArgument,
    InvalidChoice,
)

log = logging.getLogger(__name__)


class ActionTest(TestCase):
    def test_action_called(self):
        # redundant with the next test, but proves it works with intended usage
        call_count = 0

        class Foo(Command):
            action = Action()

            @action.register
            def bar(self):
                nonlocal call_count
                call_count += 1

        Foo.parse(['bar']).run()
        self.assertEqual(call_count, 1)

    def test_action_called_mock(self):
        mock = Mock(__name__='bar')

        class Foo(Command):
            action = Action()
            action.register(mock)

        foo = Foo.parse(['bar'])
        foo.run()
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args.args[0], foo)

    def test_action_wrong(self):
        class Foo(Command):
            action = Action()
            action(Mock(__name__='bar'))

        with self.assertRaises(InvalidChoice):
            Foo.parse(['baz']).main()

    def test_action_missing(self):
        class Foo(Command):
            action = Action()
            action.register(Mock(__name__='bar'))

        with self.assertRaises(MissingArgument):
            Foo.parse([]).main()

    def test_custom_name(self):
        call_count = 0

        class Foo(Command):
            action = Action()

            @action.register('bar-baz')
            def bar(self):
                nonlocal call_count
                call_count += 1

        with self.assertRaises(InvalidChoice):
            Foo.parse(['bar']).run()

        Foo.parse(['bar-baz']).run()
        self.assertEqual(call_count, 1)

    def test_invalid_names(self):
        for name in ('baz\n', 'a\nb', '\x00', '-baz', '--baz'):
            with self.subTest(name=name), self.assertRaises(ParameterDefinitionError):

                class Foo(Command):
                    action = Action()
                    action(name)(Mock(__name__='bar'))

    def test_positional_allowed_after_action(self):
        class Foo(Command):
            action = Action(help='The action to take')
            text = Positional(nargs='+')
            action(Mock(__name__='foo'))

        foo = Foo.parse(['foo', 'bar'])
        self.assertTrue(foo.args['action'])
        self.assertEqual(foo.text, ['bar'])

    def test_reject_double_choice(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                action = Action()
                action('foo', choice='foo')(Mock(__name__='foo'))


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
