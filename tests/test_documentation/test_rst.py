#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser import Command, SubCommand
from cli_command_parser.formatting.restructured_text import rst_bar, rst_header, rst_list_table, rst_directive, RstTable
from cli_command_parser.testing import ParserTest, TemporaryDir
from cli_command_parser.documentation import load_commands, render_command_rst, top_level_commands, RstWriter

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data')
THIS_DATA_DIR = TEST_DATA_DIR.joinpath('test_rst')
CMD_CASES_DIR = TEST_DATA_DIR.joinpath('command_test_cases')
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')
LIB_DIR = THIS_FILE.parents[2].joinpath('lib', 'cli_command_parser')


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


class RstWriterTest(ParserTest):
    def test_write_package_rsts(self):
        commands_expected = """
Commands Module
===============

.. currentmodule:: cli_command_parser.commands

.. automodule:: cli_command_parser.commands
   :members:
   :undoc-members:
   :show-inheritance:
        """
        index_prefix_expected = 'API Documentation\n*****************\n\n.. toctree::\n    :maxdepth: 4\n\n'
        index_middle_expected = '\n    api/cli_command_parser.commands\n    api/cli_command_parser.config\n'

        with TemporaryDir() as tmp_path:
            writer = RstWriter(tmp_path, skip_modules={'cli_command_parser.compat'})
            writer.document_package(LIB_DIR.name, LIB_DIR, name='api', header='API Documentation')

            index_path = tmp_path.joinpath('api.rst')
            self.assertTrue(index_path.is_file())
            index_content = index_path.read_text()
            self.assertTrue(index_content.startswith(index_prefix_expected))
            self.assert_str_contains(index_middle_expected, index_content)

            api_dir = tmp_path.joinpath('api')
            self.assertTrue(api_dir.is_dir())
            self.assertFalse(api_dir.joinpath('cli_command_parser.compat.rst').exists())

            commands_path = api_dir.joinpath('cli_command_parser.commands.rst')
            self.assertTrue(commands_path.is_file())
            self.assert_strings_equal(commands_expected.strip(), commands_path.read_text().strip())

    def test_write_script_rsts(self):
        index_prefix_expected = 'Example Scripts\n***************\n\n.. toctree::\n    :maxdepth: 4\n\n'
        index_middle_expected = '\n    examples/custom_inputs\n    examples/echo\n'

        with TemporaryDir() as tmp_path:
            writer = RstWriter(tmp_path)
            writer.document_scripts(EXAMPLES_DIR.glob('*.py'), 'examples', index_header='Example Scripts')

            index_path = tmp_path.joinpath('examples.rst')
            self.assertTrue(index_path.is_file())
            index_content = index_path.read_text()
            self.assertTrue(index_content.startswith(index_prefix_expected))
            self.assert_str_contains(index_middle_expected, index_content)

            scripts_dir = tmp_path.joinpath('examples')
            self.assertTrue(scripts_dir.is_dir())

            echo_exp_rst_path = THIS_DATA_DIR.joinpath('echo.rst')
            echo_path = scripts_dir.joinpath('echo.rst')
            self.assertTrue(echo_path.is_file())
            self.assert_strings_equal(echo_exp_rst_path.read_text().strip(), echo_path.read_text().strip())

    def test_write_script_rst_with_replacements(self):
        with TemporaryDir() as tmp_path:
            RstWriter(tmp_path).document_script(
                EXAMPLES_DIR.joinpath('echo.py'), name='ECHOECHOECHO', replacements={'echo.py': 'test/echo/test.py'}
            )
            echo_path = tmp_path.joinpath('ECHOECHOECHO.rst')
            self.assertTrue(echo_path.is_file())
            rst = echo_path.read_text()
            self.assertTrue(rst.startswith('ECHOECHOECHO\n************\n\n'))
            self.assert_str_contains('::\n\n    usage: test/echo/test.py [TEXT] [--help]', rst)

    def test_write_script_rsts_no_index(self):
        with TemporaryDir() as tmp_path:
            RstWriter(tmp_path).document_scripts(EXAMPLES_DIR.glob('*.py'), 'examples')
            self.assertFalse(tmp_path.joinpath('examples.rst').is_file())

    def test_write_rst_dry_run(self):
        with TemporaryDir() as tmp_path:
            with self.assertLogs('cli_command_parser.documentation', 'DEBUG') as log_ctx:
                RstWriter(tmp_path, dry_run=True).write_rst('test', 'test')

            self.assertTrue(any('[DRY RUN] Would write' in line for line in log_ctx.output))
            self.assertFalse(tmp_path.joinpath('test.rst').exists())


class CommandRstTest(ParserTest):
    def test_basic_subcommand_no_help(self):
        expected = THIS_DATA_DIR.joinpath('basic_subcommand_no_help.rst').read_text('utf-8')

        class Base(Command, doc_name='basic_subcommand_no_help', prog='foo.py', show_docstring=False, add_help=False):
            sub_cmd = SubCommand()

        class Foo(Base):
            pass

        self.assert_strings_equal(expected, render_command_rst(Base, fix_name=False))


class ExampleRstFormatTest(ParserTest):
    def test_examples_shared_logging_init(self):
        expected = THIS_DATA_DIR.joinpath('shared_logging_init.rst').read_text('utf-8')
        commands = load_commands(EXAMPLES_DIR.joinpath('shared_logging_init.py'))
        self.assertSetEqual({'Base', 'Show'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))
        with self.subTest(fix_name=True):
            self.assert_strings_equal(expected, render_command_rst(commands['Base']))

        with self.subTest(fix_name=False):
            rendered = render_command_rst(commands['Base'], fix_name=False)
            self.assertTrue(rendered.startswith('shared_logging_init\n*******************\n'))

    def test_examples_advanced_subcommand(self):
        commands = load_commands(EXAMPLES_DIR.joinpath('advanced_subcommand.py'))
        self.assertSetEqual({'Base', 'Foo', 'Bar', 'Baz'}, set(commands))
        self.assertSetEqual({'Base'}, set(top_level_commands(commands)))


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
