#!/usr/bin/env python

from abc import ABC
from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, SubCommand, Counter, Option, Positional, Flag, TriFlag
from cli_command_parser.exceptions import CommandDefinitionError, MissingArgument
from cli_command_parser.formatting.commands import get_formatter
from cli_command_parser.testing import RedirectStreams, ParserTest, get_help_text


class SubCommandTest(ParserTest):
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

    def test_2_sub_cmd_levels(self):
        class A(Command):
            sub_cmd = SubCommand()

        class B(A):
            sub_cmd = SubCommand()

        class C(B):
            x = Positional()

        class D(B):
            y = Positional()

        self.assertEqual('1', A.parse(['b', 'c', '1']).x)
        self.assertEqual('2', A.parse(['b', 'd', '2']).y)

    def test_choices(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, choices=('bar', 'bars')):
            baz = Flag('-b')

        success_cases = [
            (['bar', '-b'], {'baz': True, 'sub_cmd': 'bar'}),
            (['bars', '-b'], {'baz': True, 'sub_cmd': 'bars'}),
        ]
        self.assert_parse_results_cases(Foo, success_cases)

    def test_middle_abc_subcommand(self):
        class Base(Command):
            sub_cmd = SubCommand()
            foo = Option('-f')

        class Mid(Base, ABC):
            bar: int = Option('-b')

        class A(Mid):
            baz = Option('-B')

        class B(Mid):
            baz = Option('-B')

        with self.subTest(case='params registered'):
            cases = [(A(), (Base.foo, Mid.bar, A.baz)), (B(), (Base.foo, Mid.bar, B.baz))]
            for cmd, params in cases:
                cmd_opts = cmd.ctx.params.options
                for param in params:
                    self.assertIn(param, cmd_opts)

        with self.subTest(case='help text'):
            help_text = get_help_text(Base)
            self.assertIn('Subcommands:\n  {a|b}\n', help_text)
            self.assertNotRegex(help_text, r'\bmid\b')

        with self.subTest(case='parsing'):
            success_cases = [
                (['a', '-b1', '-B', 'a'], {'foo': None, 'bar': 1, 'baz': 'a', 'sub_cmd': 'a'}),
                (['b', '-b2', '-B', 'a'], {'foo': None, 'bar': 2, 'baz': 'a', 'sub_cmd': 'b'}),
                (['a'], {'foo': None, 'bar': None, 'baz': None, 'sub_cmd': 'a'}),
                (['b'], {'foo': None, 'bar': None, 'baz': None, 'sub_cmd': 'b'}),
            ]
            self.assert_parse_results_cases(Base, success_cases)
            self.assert_parse_fails(Base, ['mid'])

    def test_config_inherited(self):
        class Base(Command, option_name_mode='-'):
            sub_cmd = SubCommand()

        class Foo(Base):
            a_b = Flag()
            a_c = TriFlag()

        self.assertEqual(['--a-b'], Foo.a_b.option_strs.long)
        self.assertEqual(['--a-b'], Foo.a_b.option_strs.display_long)
        self.assertEqual(['--a-c'], Foo.a_c.option_strs.display_long_primary)
        self.assertEqual(['--no-a-c'], Foo.a_c.option_strs.display_long_alt)
        formatter = get_formatter(Foo)
        help_text = formatter.format_help()
        rst_text = formatter.format_rst(no_sys_argv=True)
        for expected in ('--a-b', '--a-c', '--no-a-c'):
            with self.subTest(expected=expected):
                self.assertIn(expected, help_text)
                self.assertIn(expected, rst_text)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
