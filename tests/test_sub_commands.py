#!/usr/bin/env python

from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command, SubCommand, Counter, Option, Positional
from cli_command_parser.exceptions import CommandDefinitionError, MissingArgument
from cli_command_parser.testing import RedirectStreams


class SubCommandTest(TestCase):
    def test_auto_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class FooBar(Foo, choice='bar'):
            pass

        class Baz(Foo, choice='baz'):
            pass

        self.assertNotIn('foo_bar', Foo.sub_cmd.choices)
        self.assertIsInstance(Foo.parse(['bar']), FooBar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_manual_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        @Foo.sub_cmd.register()
        class FooBar(Command):
            pass

        @Foo.sub_cmd.register
        class Bar(Command):
            pass

        @Foo.sub_cmd.register('baz')
        class Baz(Command):
            pass

        self.assertIsInstance(Foo.parse(['foo_bar']), FooBar)
        self.assertIsInstance(Foo.parse(['bar']), Bar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_mixed_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, choice='bar'):
            pass

        @Foo.sub_cmd.register(choice='baz', help='test')
        class Baz(Command):
            pass

        self.assertIsInstance(Foo.parse(['bar']), Bar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_space_in_cmd(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, choice='bar baz'):
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

        class Bar(Foo, choice='bar'):
            pass

        with self.assertRaises(MissingArgument):
            Foo.parse([])

    def test_parent_param_inherited(self):
        class Foo(Command):
            sub_cmd = SubCommand()
            verbose = Counter('-v')

        class Bar(Foo, choice='bar'):
            pass

        cmd = Foo.parse(['bar', '-v'])
        self.assertIsInstance(cmd, Bar)
        self.assertEqual(cmd.verbose, 1)

    def test_default_choice_registered(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class FooBar(Foo):
            pass

        self.assertIn('foo_bar', Foo.sub_cmd.choices)
        self.assertIsInstance(Foo.parse(['foo_bar']), FooBar)

    def test_missing_sub_cmd_but_help(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class FooBar(Foo):
            pass

        with RedirectStreams() as streams, self.assertRaises(SystemExit):
            Foo.parse_and_run(['-h'])

        self.assertIn('--help, -h', streams.stdout)

    def test_optional_sub_cmd_runs_base_main(self):
        class Foo(Command):
            sub_cmd = SubCommand(required=False)
            main = Mock()

        class Bar(Foo):
            pass

        Foo.parse_and_run([])
        self.assertTrue(Foo.main.called)

    def test_local_choices(self):
        base, d, e = Mock(), Mock(), Mock()

        class Find(Command):
            sub_cmd = SubCommand(local_choices=('a', 'b', 'c'))
            format = Option('-f', choices=('plain', 'json'))
            query = Option('-q')
            main = base

        class FindD(Find, choice='d'):
            name = Positional()
            main = d

        class FindE(Find, choice='e'):
            num = Positional()
            main = e

        with self.subTest(sub_cmd='a'):
            find = Find.parse_and_run(['a'])
            self.assertEqual((1, 0, 0), (base.call_count, d.call_count, e.call_count))
            self.assertEqual('a', find.sub_cmd, f'Parsed: {find.ctx.get_parsed()}')

        with self.subTest(sub_cmd='d'):
            Find.parse_and_run(['d', 'test'])
            self.assertEqual((1, 1, 0), (base.call_count, d.call_count, e.call_count))

        with self.subTest(sub_cmd='e'):
            Find.parse_and_run(['e', '1'])
            self.assertEqual((1, 1, 1), (base.call_count, d.call_count, e.call_count))


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
