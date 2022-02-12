#!/usr/bin/env python

import logging
from unittest import TestCase, main

from command_parser import Command, Counter, Option, Flag
from command_parser.exceptions import (
    NoSuchOption,
    UsageError,
    ParameterDefinitionError,
    CommandDefinitionError,
    ParamUsageError,
    MissingArgument,
)
from command_parser.parameters import parameter_action, PassThru
from command_parser.utils import Args

log = logging.getLogger(__name__)


class InternalsTest(TestCase):
    def test_param_knows_command(self):
        class Foo(Command):
            foo = Option('-f', choices=('a', 'b'))

        self.assertIs(Foo.foo.command, Foo)


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
            Foo.parser()


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


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
