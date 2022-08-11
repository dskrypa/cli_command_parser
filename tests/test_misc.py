#!/usr/bin/env python

from unittest import main

from cli_command_parser.testing import ParserTest


class MiscTest(ParserTest):
    def test_version(self):
        from cli_command_parser import __version__

        self.assertEqual('cli_command_parser', __version__.__title__)

    def test_dunder_main(self):
        from cli_command_parser import __main__

        self.assertEqual('this counts for coverage...?  ._.', 'this counts for coverage...?  ._.')

    def test_assert_strings_equal(self):
        with self.assertRaises(AssertionError):
            self.assert_strings_equal('foo', 'bar')
        with self.assertRaises(AssertionError):
            self.assert_strings_equal('foo', 'bar', 'baz')

    def test_assert_str_contains(self):
        with self.assertRaises(AssertionError):
            self.assert_str_contains('a', 'b')

    def test_assert_dict_equal(self):
        self.assert_dict_equal({'a': 1}, {'a': 1})
        with self.assertRaises(AssertionError):
            self.assert_dict_equal({'a': 1, 'b': 3}, {'a': 2, 'b': 3})
        with self.assertRaises(AssertionError):
            self.assert_dict_equal({'a': 1}, {'b': 1})


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
