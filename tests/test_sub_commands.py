#!/usr/bin/env python

import logging
from unittest import TestCase, main

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

        self.assertIsInstance(Foo.parse(['bar']), Bar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_manual_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        @Foo.sub_cmd.register
        class Bar(Command, cmd='bar'):
            pass

        @Foo.sub_cmd.register
        class Baz(Command, cmd='baz'):
            pass

        self.assertIsInstance(Foo.parse(['bar']), Bar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_mixed_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar'):
            pass

        @Foo.sub_cmd.register
        class Baz(Command, cmd='baz'):
            pass

        self.assertIsInstance(Foo.parse(['bar']), Bar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_space_in_cmd(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar baz'):
            pass

        self.assertIsInstance(Foo.parse(['bar', 'baz']), Bar)
        self.assertIsInstance(Foo.parse(['bar baz']), Bar)

    def test_sub_cmd_cls_required(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        with self.assertRaises(CommandDefinitionError):
            Foo.parse([])

    def test_sub_cmd_value_required(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, cmd='bar'):
            pass

        with self.assertRaises(MissingArgument):
            Foo.parse([])

    def test_parent_param_inherited(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            verbose = Counter('-v')

        class Bar(Foo, cmd='bar'):
            pass

        cmd = Foo.parse(['bar', '-v'])
        self.assertIsInstance(cmd, Bar)
        self.assertEqual(cmd.verbose, 1)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
