#!/usr/bin/env python

from unittest import main

from cli_command_parser.formatting.restructured_text import rst_bar, rst_header, rst_list_table, rst_directive, RstTable
from cli_command_parser.testing import ParserTest


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

    def test_rst_list_table(self):
        expected = """
.. list-table::
    :widths: 21 75

    * - | ``--help``, ``-h``
      - | Show this help message and exit
    * - | ``--verbose``, ``-v``
      - | Increase logging verbosity (can specify multiple times)
        """
        data = {
            '``--help``, ``-h``': 'Show this help message and exit',
            '``--verbose``, ``-v``': 'Increase logging verbosity (can specify multiple times)',
        }
        self.assert_strings_equal(expected, rst_list_table(data), trim=True)

    def test_basic_directive(self):
        self.assertEqual('.. math::', rst_directive('math'))


class RstTableTest(ParserTest):
    def test_table_repr(self):
        self.assertTrue(repr(RstTable()).startswith('<RstTable[use_table_directive='))

    def test_table_insert(self):
        table = RstTable(use_table_directive=False)
        table.add_row('x', 'y', 'z')
        table.add_row('a', 'b', 'c', index=0)
        expected = '+---+---+---+\n| a | b | c |\n+---+---+---+\n| x | y | z |\n+---+---+---+\n'
        self.assert_strings_equal(expected, str(table))

    def test_table_with_header_row(self):
        rows = [{'foo': '123', 'bar': '234'}, {'foo': '345', 'bar': '456'}]
        expected = """
+-----+-----+
| foo | bar |
+=====+=====+
| 123 | 234 |
+-----+-----+
| 345 | 456 |
+-----+-----+
        """.lstrip()
        with self.subTest(case='from_dicts'):
            table = RstTable.from_dicts(rows, auto_headers=True, use_table_directive=False)
            self.assert_strings_equal(expected, str(table), trim=True)
        with self.subTest(case='add_dict_rows'):
            table = RstTable(use_table_directive=False)
            table.add_dict_rows(rows, add_header=True)
            self.assert_strings_equal(expected, str(table), trim=True)

    def test_table_with_columns(self):
        rows = [{'foo': '123', 'bar': '234'}, {'foo': '345', 'bar': '456'}]
        table = RstTable.from_dicts(rows, columns=('foo',), use_table_directive=False)
        self.assert_strings_equal('+-----+\n| 123 |\n+-----+\n| 345 |\n+-----+\n', str(table))


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
