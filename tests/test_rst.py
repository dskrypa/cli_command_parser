#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import load_commands, get_rst

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parent.joinpath('data', 'test_rst')
EXAMPLES_DIR = THIS_FILE.parents[1].joinpath('examples')


class RstFormatTest(ParserTest):
    def test_examples_shared_logging_init(self):
        expected = TEST_DATA_DIR.joinpath('shared_logging_init.rst').read_text('utf-8')
        script_path = EXAMPLES_DIR.joinpath('shared_logging_init.py')
        commands = load_commands(script_path)
        self.assertIn('Base', commands)
        self.assertIn('Show', commands)
        self.assertEqual(2, len(commands))
        self.assert_strings_equal(expected, get_rst(commands['Base']))

    def test_examples_hello_world(self):
        expected = TEST_DATA_DIR.joinpath('hello_world.rst').read_text('utf-8')
        script_path = EXAMPLES_DIR.joinpath('hello_world.py')
        commands = load_commands(script_path)
        self.assertIn('HelloWorld', commands)
        self.assertEqual(1, len(commands))
        self.assert_strings_equal(expected, get_rst(commands['HelloWorld']), trim=True)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
