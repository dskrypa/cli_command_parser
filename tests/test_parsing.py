#!/usr/bin/env python

from unittest import TestCase, main

from command_parser import Command
from command_parser.exceptions import NoSuchOption, BadArgument, ParamsMissing
from command_parser.parameters import Positional, Option, Flag


class ParamComboTest(TestCase):
    def test_flag_and_option(self):
        class Ipython(Command):
            interactive = Flag('-i')
            module = Option('-m')

        for case in (['-im', 'lib.command_parser'], ['-i', '-m', 'lib.command_parser']):
            with self.subTest(case=case):
                cmd = Ipython.parse(case)
                self.assertTrue(cmd.interactive)
                self.assertEqual(cmd.module, 'lib.command_parser')

    def test_pos_after_optional(self):
        class Foo(Command, error_handler=None):
            cmd = Positional(help='The command to perform')
            id = Positional(help='The ID to act upon')
            auth = Option('-a', choices=('a', 'b'), help='Auth mode')

        foo = Foo.parse_and_run(['foo', '-a', 'b', 'bar'])
        self.assertEqual(foo.cmd, 'foo')
        self.assertEqual(foo.id, 'bar')
        self.assertEqual(foo.auth, 'b')
        self.assertIn('cmd', foo.args)
        self.assertIn(Foo.cmd, foo.args)
        self.assertNotIn('bar', foo.args)

        with self.assertRaises(ParamsMissing):
            Foo.parse_and_run(['foo', '-a', 'b'])

    def test_combined_flags(self):
        class Foo(Command):
            foo = Flag('-f')
            bar = Flag('-b')

        foo = Foo.parse(['-fb'])
        self.assertTrue(foo.foo)
        self.assertTrue(foo.bar)


class NumericValueTest(TestCase):
    # def setUp(self):
    #     print()
    #
    # def subTest(self, *args, **kwargs):
    #     print()
    #     return super().subTest(*args, **kwargs)

    def test_int_option(self):
        class Foo(Command, error_handler=None):
            bar: int = Option()

        foo = Foo.parse(['--bar', '-1'])
        self.assertEqual(-1, foo.bar)

        for val, exc in {'-1.5': NoSuchOption, '1.5': BadArgument, 'a': BadArgument}.items():
            with self.subTest(val=val), self.assertRaises(exc):
                Foo.parse(['--bar', val])

    def test_int_positional(self):
        class Foo(Command, error_handler=None):
            bar: int = Positional()

        foo = Foo.parse(['-1'])
        self.assertEqual(-1, foo.bar)

        for val in ('-1.5', '1.5', '-1.5.1', '1.5.1', 'a'):
            with self.subTest(val=val), self.assertRaises(BadArgument):
                Foo.parse([val])

    def test_float_option(self):
        class Foo(Command, error_handler=None):
            bar: float = Option()

        for key, val in {'1': 1, '-1': -1, '-1.5': -1.5, '1.5': 1.5, '0': 0}.items():
            with self.subTest(val=val):
                foo = Foo.parse(['--bar', key])
                self.assertEqual(val, foo.bar)

        for val, exc in {'-1.5.1': NoSuchOption, '1.5.1': BadArgument, 'a': BadArgument}.items():
            with self.subTest(val=val), self.assertRaises(exc):
                Foo.parse(['--bar', val])

    def test_float_positional(self):
        class Foo(Command, error_handler=None):
            bar = Positional(type=float)

        for key, val in {'1': 1, '-1': -1, '-1.5': -1.5, '1.5': 1.5, '0': 0}.items():
            with self.subTest(val=val):
                foo = Foo.parse([key])
                self.assertEqual(val, foo.bar)

        for val in ('-1.5.1', '1.5.1', 'a'):
            with self.subTest(val=val), self.assertRaises(BadArgument):
                Foo.parse([val])


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
