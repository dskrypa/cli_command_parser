#!/usr/bin/env python

import logging
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import Command, SubCommand, CommandDefinitionError, MissingArgument, Counter

log = logging.getLogger(__name__)


class SubCommandTest(TestCase):
    def test_auto_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar'):
            pass

        class Baz(Foo, cmd='baz'):
            pass

        self.assertIsInstance(Foo(['bar']), Bar)
        self.assertIsInstance(Foo(['baz']), Baz)

    def test_manual_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        @Foo.sub_cmd.register
        class Bar(Command, cmd='bar'):
            pass

        @Foo.sub_cmd.register
        class Baz(Command, cmd='baz'):
            pass

        self.assertIsInstance(Foo(['bar']), Bar)
        self.assertIsInstance(Foo(['baz']), Baz)

    def test_mixed_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar'):
            pass

        @Foo.sub_cmd.register
        class Baz(Command, cmd='baz'):
            pass

        self.assertIsInstance(Foo(['bar']), Bar)
        self.assertIsInstance(Foo(['baz']), Baz)

    def test_space_in_cmd(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar baz'):
            pass

        self.assertIsInstance(Foo(['bar', 'baz']), Bar)
        self.assertIsInstance(Foo(['bar baz']), Bar)

    def test_sub_cmd_cls_required(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo([])

    def test_sub_cmd_value_required(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar'):
            pass

        with self.assertRaises(MissingArgument):
            Foo([])

    def test_parent_param_inherited(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            verbose = Counter('-v')

        class Bar(Foo, cmd='bar'):
            pass

        cmd = Foo(['bar', '-v'])
        self.assertIsInstance(cmd, Bar)
        self.assertEqual(cmd.verbose, 1)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
