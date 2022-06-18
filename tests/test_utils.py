#!/usr/bin/env python

from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser.utils import camel_to_snake_case, get_args


class UtilsTest(TestCase):
    def test_camel_to_snake(self):
        self.assertEqual('foo_bar', camel_to_snake_case('FooBar'))
        self.assertEqual('foo bar', camel_to_snake_case('FooBar', ' '))
        self.assertEqual('foo', camel_to_snake_case('Foo'))

    def test_get_args(self):
        # This is for coverage in 3.9+ for the get_args compatibility wrapper, to mock the attr present in 3.8 & below
        self.assertEqual((), get_args(Mock(_special=True)))


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
