#!/usr/bin/env python

import logging
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import Command, Action, InvalidChoice, MissingArgument

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

        Foo(['bar']).run()
        self.assertEqual(call_count, 1)

    def test_action_called_mock(self):
        mock = MagicMock(__name__='bar')
        class Foo(Command):
            action = Action()
            action.register(mock)

        foo = Foo(['bar'])
        foo.run()
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args.args[0], foo)

    def test_action_wrong(self):
        mock = MagicMock(__name__='bar')
        class Foo(Command):
            action = Action()
            action.register(mock)

        with self.assertRaises(InvalidChoice):
            Foo(['baz']).run()

    def test_action_missing(self):
        mock = MagicMock(__name__='bar')
        class Foo(Command):
            action = Action()
            action.register(mock)

        with self.assertRaises(MissingArgument):
            Foo([]).run()


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
