#!/usr/bin/env python

import logging
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.append(Path(__file__).parents[1].joinpath('lib').as_posix())
from command_parser import ParameterGroup, Command, Flag, UsageError

log = logging.getLogger(__name__)


class GroupTest(TestCase):
    def test_params_know_own_group(self):
        class Foo(Command):
            foo = Flag('-f')
            with ParameterGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        self.assertIs(Foo.foo.group, None)
        self.assertIs(Foo.bar.group, Foo.group)
        self.assertIs(Foo.baz.group, Foo.group)

    def test_me_ok(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse(['-b'])
        self.assertTrue(foo.bar)
        self.assertFalse(foo.baz)

    def test_me_conflict(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        with self.assertRaises(UsageError):
            Foo.parse(['-b', '-B'])

    def test_me_skipped(self):
        class Foo(Command):
            with ParameterGroup(mutually_exclusive=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse([])
        self.assertFalse(foo.bar)
        self.assertFalse(foo.baz)

    def test_md_ok(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse(['-b', '-B'])
        self.assertTrue(foo.bar)
        self.assertTrue(foo.baz)

    def test_md_conflict(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        with self.assertRaises(UsageError):
            Foo.parse(['-b'])

        with self.assertRaises(UsageError):
            Foo.parse(['-B'])

    def test_md_skipped(self):
        class Foo(Command):
            with ParameterGroup(mutually_dependent=True) as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse([])
        self.assertFalse(foo.bar)
        self.assertFalse(foo.baz)

    def test_plain_1(self):
        class Foo(Command):
            with ParameterGroup() as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse(['-b'])
        self.assertTrue(foo.bar)
        self.assertFalse(foo.baz)

        foo = Foo.parse(['-B'])
        self.assertFalse(foo.bar)
        self.assertTrue(foo.baz)

    def test_plain_2(self):
        class Foo(Command):
            with ParameterGroup() as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse(['-b', '-B'])
        self.assertTrue(foo.bar)
        self.assertTrue(foo.baz)

    def test_plain_skipped(self):
        class Foo(Command):
            with ParameterGroup() as group:
                bar = Flag('-b')
                baz = Flag('-B')

        foo = Foo.parse([])
        self.assertFalse(foo.bar)
        self.assertFalse(foo.baz)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
