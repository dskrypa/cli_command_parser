#!/usr/bin/env python

import logging
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser import Command, Counter, Option, Flag
from command_parser.exceptions import (
    NoSuchOption,
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
    BadArgument,
)
from command_parser.parameters import parameter_action, PassThru, Positional, SubCommand
from command_parser.args import Args

log = logging.getLogger(__name__)


class InternalsTest(TestCase):
    def test_param_knows_command(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertIs(Foo.foo.command, Foo)


class PositionalTest(TestCase):
    def test_extra_positional_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', 'baz'])

        foo = Foo.parse(['bar', 'baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['baz'])


class OptionTest(TestCase):
    def test_choice_ok(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertEqual(Foo.parse(['-f', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['-f', 'b']).foo, 'b')
        self.assertEqual(Foo.parse(['--foo', 'a']).foo, 'a')
        self.assertEqual(Foo.parse(['--foo', 'b']).foo, 'b')

    def test_choice_bad(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        with self.assertRaises(UsageError):
            Foo.parse(['-f', 'c'])

    def test_instance_values(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        a = Foo.parse(['-f', 'a'])
        b = Foo.parse(['-f', 'b'])
        self.assertEqual(a.foo, 'a')
        self.assertEqual(b.foo, 'b')

    def test_triple_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['---'], ['---bar'], ['--bar', '---'], ['--bar', '---bar']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_misc_dash_rejected(self):
        class Foo(Command):
            bar = Flag()

        for case in (['----'], ['----bar'], ['--bar', '----'], ['--bar', '----bar'], ['-'], ['--bar', '-']):
            with self.subTest(case=case), self.assertRaises(NoSuchOption):
                Foo.parse(case)

    def test_extra_long_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz'])

        foo = Foo.parse(['bar', '--baz'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '--baz', 'a'])

        foo = Foo.parse(['bar', '--baz', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['--baz', 'a'])

    def test_extra_short_option_deferred(self):
        class Foo(Command):
            bar = Positional()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b'])

        foo = Foo.parse(['bar', '-b'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b', 'a'])

        foo = Foo.parse(['bar', '-b', 'a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b', 'a'])

        with self.assertRaises(NoSuchOption):
            Foo.parse(['bar', '-b=a'])

        foo = Foo.parse(['bar', '-b=a'], allow_unknown=True)
        self.assertEqual(foo.args.remaining, ['-b=a'])

    def test_value_missing(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Option()

        cases = (['--foo', '--bar'], ['--bar', '--foo'], ['-f', '--bar'], ['--bar', '-f'])
        for case in cases:
            with self.subTest(case=case), self.assertRaises(MissingArgument):
                Foo.parse(case)

        self.assertTrue(Foo.parse(['--foo']).foo)

    def test_short_value_invalid(self):
        class Foo(Command):
            foo = Flag()
            bar = Option()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--bar', '-f'])

    def test_invalid_value(self):
        class Foo(Command):
            bar = Option(type=Mock(side_effect=TypeError))

        with self.assertRaises(BadArgument):
            Foo.parse(['--bar', '1'])


class CounterTest(TestCase):
    def test_counter_default(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse([]).verbose, 0)

    def test_counter_1(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        self.assertEqual(Foo.parse(['-v']).verbose, 1)
        self.assertEqual(Foo.parse(['--verbose']).verbose, 1)
        with self.assertRaises(NoSuchOption):
            Foo.parse(['-verbose'])

    def test_counter_multi(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-{}'.format('v' * n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose'] * n).verbose, n)

    def test_counter_num_no_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v{n}']).verbose, n)

    def test_counter_num_space(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse(['-v', str(n)]).verbose, n)
                self.assertEqual(Foo.parse(['--verbose', str(n)]).verbose, n)

    def test_counter_num_eq(self):
        class Foo(Command):
            verbose: int = Counter('-v')

        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo.parse([f'-v={n}']).verbose, n)
                self.assertEqual(Foo.parse([f'--verbose={n}']).verbose, n)

    def test_combined_counters(self):
        class Foo(Command):
            foo = Counter('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (2, 2),
            '-fbfb': (2, 2),
            '-ffb': (2, 1),
            '-fbf': (2, 1),
            '-fbb': (1, 2),
            '-bfb': (1, 2),
            '-bb': (0, 2),
            '-ff': (2, 0),
            ('-fb', '3'): (1, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)

    def test_counter_flag_combo(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Counter('-b')

        cases = {
            '-ffbb': (True, 2),
            '-fbfb': (True, 2),
            '-ffb': (True, 1),
            '-fbf': (True, 1),
            '-fbb': (True, 2),
            '-bfb': (True, 2),
            '-bb': (False, 2),
            '-ff': (True, 0),
            ('-fb', '3'): (True, 3),
        }
        for case, (f, b) in cases.items():
            foo = Foo.parse([case] if isinstance(case, str) else case)
            self.assertEqual(foo.foo, f)
            self.assertEqual(foo.bar, b)


class PassThruTest(TestCase):
    def test_pass_thru(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru()

        foo = Foo.parse(['--bar', '--', 'test', 'one', 'two', 'three'])
        self.assertTrue(foo.bar)
        self.assertEqual(foo.baz, ['test', 'one', 'two', 'three'])

        foo = Foo.parse(['--', '--bar', '--', 'test', 'one', 'two', 'three'])
        self.assertFalse(foo.bar)
        self.assertEqual(foo.baz, ['--bar', '--', 'test', 'one', 'two', 'three'])

        foo = Foo.parse(['--bar', '--'])
        self.assertTrue(foo.bar)
        self.assertEqual(foo.baz, [])

        foo = Foo.parse(['--bar'])
        self.assertTrue(foo.bar)
        self.assertIs(foo.baz, None)

    def test_pass_thru_missing(self):
        class Foo(Command):
            bar = Flag()
            baz = PassThru(required=True)

        with self.assertRaises(MissingArgument):
            Foo.parse([])

    def test_multiple_rejected(self):
        class Foo(Command):
            bar = PassThru()
            baz = PassThru()

        with self.assertRaises(CommandDefinitionError):
            Foo.parser  # noqa

    def test_double_dash_without_pass_thru_rejected(self):
        class Foo(Command):
            bar = Flag()

        with self.assertRaises(NoSuchOption):
            Foo.parse(['--'])


class MiscParameterTest(TestCase):
    def test_unregistered_action_rejected(self):
        with self.assertRaises(ParameterDefinitionError):
            Flag(action='foo')

    def test_empty_choices(self):
        with self.assertRaises(ParameterDefinitionError):
            Option(choices=())

    def test_action_is_parameter_action(self):
        self.assertIsInstance(Flag.store_const, parameter_action)

    def test_re_assign_rejected(self):
        option = Option(action='store')
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_too_many_rejected(self):
        option = Option(action='append', nargs=1)
        args = Args([])
        option.take_action(args, 'foo')
        with self.assertRaises(ParamUsageError):
            option.take_action(args, 'foo')

    def test_non_none_rejected(self):
        flag = Flag()
        with self.assertRaises(ParamUsageError):
            flag.take_action(Args([]), 'foo')


class ParserTest(TestCase):
    def test_parser_repr(self):
        class Foo(Command):
            bar = Positional()

        rep = repr(Foo.parser)
        self.assertIn('Foo', rep)
        self.assertIn('positionals=', rep)
        self.assertIn('options=', rep)

    def test_parser_contains_recursive(self):
        class Foo(Command):
            cmd = SubCommand()

        class Bar(Foo):
            bar = Counter('-b')

        for cls in (Foo, Bar):
            parser = cls.parser
            self.assertTrue(parser.contains(Args([]), '-h'))
            self.assertFalse(parser.contains(Args([]), '-H'))
            self.assertTrue(parser.contains(Args([]), '-b=1'))
            self.assertFalse(parser.contains(Args([]), '-B=1'))
            self.assertFalse(parser.contains(Args([]), '-ba'))
            self.assertTrue(parser.contains(Args([]), '--bar=1'))
            self.assertFalse(parser.contains(Args([]), '--baz=1'))
            self.assertFalse(parser.contains(Args([]), 'baz'))
            self.assertTrue(parser.contains(Args([]), '-b=1'))
            self.assertFalse(parser.contains(Args([]), '-B=1'))
            self.assertTrue(parser.contains(Args([]), '-bb'))
            self.assertFalse(parser.contains(Args([]), '-ab'))

    def test_redefine_param_rejected(self):
        class Foo(Command):
            cmd = SubCommand()
            bar = Flag('-b')

        class Bar(Foo):
            bar = Counter('-b')

        with self.assertRaisesRegex(CommandDefinitionError, 'conflict for command=.* between params'):
            Foo.parse(['bar'])


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
