#!/usr/bin/env python

from unittest import main
from unittest.mock import Mock

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

    def test_assert_raises_contains_str(self):
        with self.assertRaises(AssertionError) as exc_ctx:
            with self.assert_raises_contains_str(ValueError, 'foo'):
                raise ValueError('bar')

        self.assertEqual("'foo' not found in 'bar'", str(exc_ctx.exception))

        with self.assertRaises(AssertionError) as exc_ctx:
            with self.assert_raises_contains_str(ValueError, 'foo'):
                pass

        self.assertEqual('ValueError not raised', str(exc_ctx.exception))

        with self.assertRaises(RuntimeError):  # The unexpected exception was allowed to propagate
            with self.assert_raises_contains_str(ValueError, 'foo'):
                raise RuntimeError('foo')

    def test_assert_parse_results_ok(self):
        cmd = Mock(ctx=Mock(get_parsed=Mock(return_value={'foo': 'bar'})))
        cmd_cls = Mock(parse=Mock(return_value=cmd))
        self.assertIs(cmd, self.assert_parse_results(cmd_cls, [], {'foo': 'bar'}))

    def test_assert_parse_results_fail(self):
        cmd = Mock(ctx=Mock(get_parsed=Mock(return_value={'foo': 'bar'})))
        cmd_cls = Mock(parse=Mock(return_value=cmd))
        with self.assertRaises(AssertionError):
            self.assert_parse_results(cmd_cls, [], {'foo': 'baz'})


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
