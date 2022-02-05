#!/usr/bin/env python

import logging
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import Command, Action, no_exit_handler, ActionFlag, ParameterGroup
from command_parser.exceptions import CommandDefinitionError, ParameterDefinitionError

log = logging.getLogger(__name__)


class ActionFlagTest(TestCase):
    def test_help_action(self):
        mock = Mock(__name__='bar')

        class Foo(Command, exc_handler=no_exit_handler):
            action = Action()
            action.register(mock)

        sio = StringIO()
        with redirect_stdout(sio):
            foo = Foo(['bar', '-h'])
            foo.run()

        self.assertTrue(sio.getvalue().startswith('usage: '))
        self.assertEqual(mock.call_count, 0)

    def test_af_func_missing(self):
        class Foo(Command):
            foo = ActionFlag()

        with self.assertRaises(ParameterDefinitionError) as ctx:
            Foo([])
        self.assertIn('No function was registered', str(ctx.exception))

    def test_af_prio_conflict(self):
        class Foo(Command):
            foo = ActionFlag()(Mock())
            bar = ActionFlag()(Mock())

        with self.assertRaises(CommandDefinitionError) as ctx:
            Foo([])

        self.assertIn('different priority values', str(ctx.exception))

    def test_af_non_me_group_conflict(self):
        class Foo(Command):
            with ParameterGroup() as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaises(CommandDefinitionError) as ctx:
            Foo([])

        self.assertIn('different priority values', str(ctx.exception))

    def test_af_md_group_conflict(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        with self.assertRaises(CommandDefinitionError) as ctx:
            Foo([])

        self.assertIn('different priority values', str(ctx.exception))

    def test_af_me_group_ok(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                foo = ActionFlag()(Mock())
                bar = ActionFlag()(Mock())

        foo = Foo([])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['foo'])
        with self.assertRaises(KeyError):
            self.assertFalse(foo.args['bar'])

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
