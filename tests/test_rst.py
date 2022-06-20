#!/usr/bin/env python

import sys
from pathlib import Path
from textwrap import dedent
from unittest import main

from cli_command_parser import Command, SubCommand
from cli_command_parser.formatting.restructured_text import rst_bar, rst_header, rst_list_table, rst_directive, RstTable
from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import (
    load_commands,
    render_command_rst,
    render_script_rst,
    top_level_commands,
    _render_commands_rst,
    import_module,
)

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
        table = RstTable(header=False)
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

    def test_basic_subcommand_no_help(self):
        expected = TEST_DATA_DIR.joinpath('basic_subcommand_no_help.rst').read_text('utf-8')

        class Base(Command, doc_name='basic_subcommand_no_help', prog='foo.py', show_docstring=False):
            sub_cmd = SubCommand()

        class Foo(Base):
            pass

        self.assert_strings_equal(expected, render_command_rst(Base, fix_name=False))


class ExampleRstFormatTest(ParserTest):
    def test_examples_shared_logging_init(self):
        expected = TEST_DATA_DIR.joinpath('shared_logging_init.rst').read_text('utf-8')
        script_path = EXAMPLES_DIR.joinpath('shared_logging_init.py')
        commands = load_commands(script_path)
        self.assertSetEqual({'Base', 'Show'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))
        with self.subTest(fix_name=True):
            self.assert_strings_equal(expected, render_command_rst(commands['Base']))

        with self.subTest(fix_name=False):
            rendered = render_command_rst(commands['Base'], fix_name=False)
            self.assertTrue(rendered.startswith('shared_logging_init\n*******************\n'))

    def test_examples_hello_world(self):
        expected = TEST_DATA_DIR.joinpath('hello_world.rst').read_text('utf-8')
        script_path = EXAMPLES_DIR.joinpath('hello_world.py')
        self.assert_strings_equal(expected, render_script_rst(script_path), trim=True)

    def test_examples_advanced_subcommand(self):
        expected = TEST_DATA_DIR.joinpath('advanced_subcommand.rst').read_text('utf-8')
        script_path = EXAMPLES_DIR.joinpath('advanced_subcommand.py')
        commands = load_commands(script_path)
        self.assertSetEqual({'Base', 'Foo', 'Bar', 'Baz'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))
        self.assert_strings_equal(expected, render_command_rst(commands['Base']), trim=True)


class DocumentationUtilsTest(ParserTest):
    def test_filter_multiple_top_cmds(self):
        class Foo(Command):
            pass

        class Bar(Command):
            pass

        commands = {'Foo': Foo, 'Bar': Bar}
        self.assertEqual(commands, top_level_commands(commands))

    def test_multi_command_rst(self):
        expected = TEST_DATA_DIR.joinpath('basic_command_multi.rst').read_text('utf-8')

        class Foo(Command, doc_name='basic_command_multi', prog='foo.py', show_docstring=False):
            pass

        class Bar(Command, doc_name='basic_command_multi', prog='foo.py', show_docstring=False):
            pass

        commands = {'Foo': Foo, 'Bar': Bar}
        self.assert_strings_equal(expected, _render_commands_rst(commands, fix_name=False), trim=True)

    def test_import_error(self):
        with self.assertRaises(ImportError):
            import_module(TEST_DATA_DIR.joinpath('hello_world.rst'))

    def test_remove_from_sys_modules_on_error(self):
        with self.assertRaises(RuntimeError):
            import_module(TEST_DATA_DIR.joinpath('runtime_error.py'))
        self.assertNotIn('runtime_error', sys.modules)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
