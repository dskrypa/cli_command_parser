#!/usr/bin/env python

import logging
from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Action, no_exit_handler, ActionFlag, ParameterGroup
from command_parser.exceptions import CommandDefinitionError, ParameterDefinitionError

log = logging.getLogger(__name__)


class ActionFlagTest(TestCase):
    def test_help_action(self):
        mock = Mock(__name__='bar')

        class Foo(Command, error_handler=no_exit_handler):
            action = Action()
            action.register(mock)

        sio = StringIO()
        with redirect_stdout(sio):
            foo = Foo.parse(['bar', '-h'])
            foo.run()

        self.assertTrue(sio.getvalue().startswith('usage: '))
        self.assertEqual(mock.call_count, 0)

    def test_af_func_missing(self):
        class Foo(Command):
            foo = ActionFlag()

        with self.assertRaisesRegex(ParameterDefinitionError, 'No function was registered'):
            Foo.parse([])

    def test_af_prio_conflict(self):
        class Foo(Command):
            foo = ActionFlag()(Mock())
            bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different priority values'):
            Foo.parse([])

    def test_af_non_me_group_conflict(self):
        class Foo(Command):
            with ParameterGroup() as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different priority values'):
            Foo.parse([])

    def test_af_md_group_conflict(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different priority values'):
            Foo.parse([])

    def test_af_me_group_ok(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        foo = Foo.parse([])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['foo'])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['bar'])

    def test_af_mixed_grouping_rejected(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())
            baz = ActionFlag()(Mock())

        with self.assertRaisesRegex(CommandDefinitionError, 'different priority values'):
            Foo.parser()

    def test_no_reassign(self):
        with self.assertRaises(CommandDefinitionError):

            class Foo(Command):
                foo = ActionFlag()(Mock())

                @foo
                def bar(self):
                    pass


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
