#!/usr/bin/env python

from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser.utils import camel_to_snake_case, get_args, Terminal
from cli_command_parser.formatting.utils import description_start_line, normalize_column


class UtilsTest(TestCase):
    def test_camel_to_snake(self):
        self.assertEqual('foo_bar', camel_to_snake_case('FooBar'))
        self.assertEqual('foo bar', camel_to_snake_case('FooBar', ' '))
        self.assertEqual('foo', camel_to_snake_case('Foo'))

    def test_get_args(self):
        # This is for coverage in 3.9+ for the get_args compatibility wrapper, to mock the attr present in 3.8 & below
        self.assertEqual((), get_args(Mock(_special=True)))

    def test_terminal_width_refresh(self):
        with patch('cli_command_parser.utils.get_terminal_size', return_value=(123, 1)):
            term = Terminal(0.01)
            self.assertEqual(123, term.width)

    def test_descr_start_middle(self):
        usage = ['a' * 10, 'a' * 15, 'a' * 5]
        self.assertEqual(2, description_start_line(usage, 5))

    def test_descr_start_no_usage(self):
        self.assertEqual(0, description_start_line((), -5))

    def test_normalize_column_uneven(self):
        result = normalize_column(('a' * 10, 'b' * 3), 5)
        self.assertListEqual(['aaaaa', 'aaaaa', 'bbb'], result)


if __name__ == '__main__':
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
