#!/usr/bin/env python

import logging
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, MagicMock

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import Command, Counter, NoSuchOption, Option, UsageError

log = logging.getLogger(__name__)


class OptionTest(TestCase):
    def test_choice_ok(self):
        class Foo(Command): foo = Option('-f', choices=('a', 'b'))  # noqa
        self.assertEqual(Foo(['-f', 'a']).foo, 'a')
        self.assertEqual(Foo(['-f', 'b']).foo, 'b')
        self.assertEqual(Foo(['--foo', 'a']).foo, 'a')
        self.assertEqual(Foo(['--foo', 'b']).foo, 'b')

    def test_choice_bad(self):
        class Foo(Command): foo = Option('-f', choices=('a', 'b'))  # noqa
        with self.assertRaises(UsageError):
            Foo(['-f', 'c'])


class CounterTest(TestCase):
    def test_counter_default(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        self.assertEqual(Foo([]).verbose, 0)

    def test_counter_1(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        self.assertEqual(Foo(['-v']).verbose, 1)
        self.assertEqual(Foo(['--verbose']).verbose, 1)
        with self.assertRaises(NoSuchOption):
            Foo(['-verbose'])

    def test_counter_multi(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        for n in range(1, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo(['-{}'.format('v' * n)]).verbose, n)
                self.assertEqual(Foo(['--verbose'] * n).verbose, n)

    def test_counter_num_no_space(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo([f'-v{n}']).verbose, n)

    def test_counter_num_space(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo(['-v', str(n)]).verbose, n)
                self.assertEqual(Foo(['--verbose', str(n)]).verbose, n)

    def test_counter_num_eq(self):
        class Foo(Command): verbose: int = Counter('-v')  # noqa
        for n in range(-10, 11):
            with self.subTest(n=n):
                self.assertEqual(Foo([f'-v={n}']).verbose, n)
                self.assertEqual(Foo([f'--verbose={n}']).verbose, n)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
