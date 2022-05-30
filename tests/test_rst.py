#!/usr/bin/env python

from pathlib import Path
from textwrap import dedent
from unittest import main

from cli_command_parser.formatting.rst import rst_bar, rst_header, rst_list_table, rst_directive, RstTable
from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import load_commands, get_rst

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parent.joinpath('data', 'test_rst')
EXAMPLES_DIR = THIS_FILE.parents[1].joinpath('examples')


class RstFormatTest(ParserTest):
    def test_rst_bar(self):
        text = 'example_text'
        bars = {rst_bar(text, i) for i in range(6)}
        self.assertEqual(6, len(bars))
        self.assertTrue(all(12 == len(bar) for bar in bars))

    def test_rst_header(self):
        text = 'example text'
        self.assertEqual('############\nexample text\n############', rst_header(text, 0, True))
        self.assertEqual('example text\n^^^^^^^^^^^^', rst_header(text, 4))

    def test_rst_table(self):
        expected = """
        .. list-table::
            :widths: 21 75

            * - | ``--help``, ``-h``
              - | Show this help message and exit
            * - | ``--verbose``, ``-v``
              - | Increase logging verbosity (can specify multiple times)
        """
        expected = dedent(expected)
        data = {
            '``--help``, ``-h``': 'Show this help message and exit',
            '``--verbose``, ``-v``': 'Increase logging verbosity (can specify multiple times)',
        }
        self.assert_strings_equal(expected, rst_list_table(data))

    def test_basic_directive(self):
        self.assertEqual('.. math::', rst_directive('math'))

    def test_table_repr(self):
        self.assertTrue(repr(RstTable()).startswith('<RstTable[header='))

    def test_table_insert(self):
        table = RstTable()
        table.add_row('x', 'y', 'z')
        table.add_row('a', 'b', 'c', index=0)
        expected = """
        +---+---+---+
        | a | b | c |
        +---+---+---+
        | x | y | z |
        +---+---+---+
        """
        expected = dedent(expected).lstrip()
        self.assert_strings_equal(expected, str(table))


class ExampleRstFormatTest(ParserTest):
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
