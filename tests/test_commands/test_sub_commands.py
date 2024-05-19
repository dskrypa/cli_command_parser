#!/usr/bin/env python

from abc import ABC
from unittest import main
from unittest.mock import Mock

from cli_command_parser import Command, Counter, Flag, Option, ParamGroup, Positional, SubCommand, TriFlag
from cli_command_parser.exceptions import CommandDefinitionError, MissingArgument, UsageError
from cli_command_parser.formatting.commands import get_formatter
from cli_command_parser.testing import ParserTest, RedirectStreams, get_help_text


class SubCommandTest(ParserTest):
    # region Registration / Definition Tests

    def test_auto_register(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class FooBar(Foo, choice='bar'):
            pass

        class Baz(Foo, choice='baz'):
            pass

        self.assertNotIn('foo_bar', Foo.sub_cmd.choices)
        self.assertIn('bar', Foo.sub_cmd.choices)
        self.assertIsInstance(Foo.parse(['bar']), FooBar)
        self.assertIsInstance(Foo.parse(['baz']), Baz)

    def test_default_choice_registered(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class FooBar(Foo):
            pass

        self.assertIn('foo_bar', Foo.sub_cmd.choices)
        self.assertIsInstance(Foo.parse(['foo_bar']), FooBar)

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

    def test_sub_cmd_cls_required(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        for args in ([], ['foo']):
            with self.assert_raises_contains_str(CommandDefinitionError, 'has no sub Commands'):
                Foo.parse(args)

    def test_choice_none_not_registered(self):
        class Foo(Command):
            sub = SubCommand()

        class Bar(Foo, choice=None):
            pass

        self.assertEqual({}, Foo.sub.choices)

    def test_help_from_description_kwarg(self):
        class Foo(Command):
            """Foo docstring"""

            sub: SubCommand = SubCommand()

        class Bar(Foo, description='Bar description'):
            pass

        self.assertEqual('Bar description', Foo.sub.choices['bar'].help)

    def test_help_from_description_docstring(self):
        class Foo(Command):
            """Foo docstring"""

            sub: SubCommand = SubCommand()

        class Bar(Foo):
            """Bar docstring"""

        self.assertEqual('Bar docstring', Foo.sub.choices['bar'].help)

    def test_help_from_help_kwarg(self):
        class Foo(Command):
            """Foo docstring"""

            sub: SubCommand = SubCommand()

        class Bar(Foo, help='Bar help'):
            pass

        self.assertEqual('Bar help', Foo.sub.choices['bar'].help)

    def test_help_from_help_not_desc_kwarg(self):
        class Foo(Command):
            """Foo docstring"""

            sub: SubCommand = SubCommand()

        class Bar(Foo, description='Bar description', help='Bar help'):
            pass

        self.assertEqual('Bar help', Foo.sub.choices['bar'].help)

    def test_empty_help_from_help_not_desc_kwarg(self):
        class Foo(Command):
            """Foo docstring"""

            sub: SubCommand = SubCommand()

        class Bar(Foo, description='Bar description', help=''):
            pass

        self.assertEqual('', Foo.sub.choices['bar'].help)

    # endregion

    # region Parsing Behavior Tests

    def test_space_in_cmd(self):
        class Foo(Command):
            sub_cmd = SubCommand()

        class Bar(Foo, choice='bar baz'):
            pass

        self.assertIsInstance(Foo.parse(['bar', 'baz']), Bar)
        self.assertIsInstance(Foo.parse(['bar baz']), Bar)

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

    # endregion

    # region Handling Multiple Choices

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

    def test_local_choices(self):
        base, d, e = Mock(), Mock(), Mock()

        class Find(Command):
            # TODO: Document local_choices usage with examples
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

    # endregion

    # region Nested Subcommands and Inheritance

    def test_2_sub_cmd_levels(self):
        class A(Command):
            sub_cmd = SubCommand()

        class B(A):
            sub_cmd = SubCommand()

        class C(B):
            x = Positional()

        class D(B):
            y = Positional()

        self.assertEqual('1', A.parse(['b', 'c', '1']).x)  # noqa
        self.assertEqual('2', A.parse(['b', 'd', '2']).y)  # noqa

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
                (['a', '-b1', '-B', 'a', '-fx'], {'foo': 'x', 'bar': 1, 'baz': 'a', 'sub_cmd': 'a'}),
                (['b', '-b2', '-B', 'a'], {'foo': None, 'bar': 2, 'baz': 'a', 'sub_cmd': 'b'}),
                (['a'], {'foo': None, 'bar': None, 'baz': None, 'sub_cmd': 'a'}),
                (['b'], {'foo': None, 'bar': None, 'baz': None, 'sub_cmd': 'b'}),
            ]
            self.assert_parse_results_cases(Base, success_cases)
            fail_cases = [['mid'], ['mid', 'a'], ['mid', 'b'], ['a', 'mid'], ['b', 'mid']]
            self.assert_parse_fails_cases(Base, fail_cases, UsageError)

    def test_middle_abc_subcommand_positional_basic(self):
        class Base(Command):
            sub = SubCommand()

        class Mid(Base, ABC):
            foo = Positional()

        class A(Mid):
            bar = Option('-B')

        success_cases = [
            (['a', 'x', '-B', 'a'], {'foo': 'x', 'bar': 'a', 'sub': 'a'}),
            (['a', 'x'], {'foo': 'x', 'bar': None, 'sub': 'a'}),
        ]
        self.assert_parse_results_cases(Base, success_cases)
        fail_cases = [['mid'], ['mid', 'a'], ['a'], ['foo', 'a']]
        self.assert_parse_fails_cases(Base, fail_cases, UsageError)

    def test_middle_abc_subcommand_with_positionals(self):
        class Base(Command, prog='foo_bar.py'):
            sub = SubCommand()

        class Mid(Base, ABC):
            foo = Positional()
            with ParamGroup():
                bar: int = Positional()

        class A(Mid):
            baz = Option('-B')

        class B(Mid):
            baz = Option('-B')

        with self.subTest(case='params registered'):
            self.assertEqual(2, len(A().ctx.params.all_positionals))
            self.assertEqual(2, len(B().ctx.params.all_positionals))

        with self.subTest(case='help text'):
            base_help_text = get_help_text(Base)
            self.assert_str_contains('Subcommands:\n  {a|b}\n', base_help_text)
            self.assertNotRegex(base_help_text, r'\bmid\b')
            expected = """usage: foo_bar.py a FOO BAR [--help] [--baz BAZ]\n
Positional arguments:\n  FOO\n
Other arguments:\n  BAR\n
Optional arguments:\n  --help, -h                  Show this help message and exit\n  --baz BAZ, -B BAZ\n"""
            self.assert_strings_equal(expected, get_help_text(A))

        with self.subTest(case='parsing'):
            success_cases = [
                (['a', 'w', '1', '-B', 'a'], {'foo': 'w', 'bar': 1, 'baz': 'a', 'sub': 'a'}),
                (['b', 'x', '2', '-B', 'a'], {'foo': 'x', 'bar': 2, 'baz': 'a', 'sub': 'b'}),
                (['a', 'y', '9'], {'foo': 'y', 'bar': 9, 'baz': None, 'sub': 'a'}),
                (['b', 'z', '9'], {'foo': 'z', 'bar': 9, 'baz': None, 'sub': 'b'}),
            ]
            self.assert_parse_results_cases(Base, success_cases)
            # fmt: off
            fail_cases = [
                ['mid'], ['mid', 'a'], ['mid', 'b'], ['a', 'mid'], ['b', 'mid'],
                ['1', 'a'], ['1', 'b'], ['a'], ['b'], ['a', 'x'], ['b', 'x'], ['x', '1'], ['x', '1', 'a'], ['1', 'x'],
            ]
            # fmt: on
            self.assert_parse_fails_cases(Base, fail_cases, UsageError)

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
        rst_text = formatter.format_rst()
        for expected in ('--a-b', '--a-c', '--no-a-c'):
            with self.subTest(expected=expected):
                self.assertIn(expected, help_text)
                self.assertIn(expected, rst_text)

    # endregion


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
