#!/usr/bin/env python

from functools import cached_property
from pathlib import Path
from unittest import main
from unittest.mock import patch

from cli_command_parser import Command, SubCommand
from cli_command_parser.documentation import load_commands, render_command_rst, RstWriter
from cli_command_parser.testing import ParserTest, TemporaryDir

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data')
THIS_DATA_DIR = TEST_DATA_DIR.joinpath('test_rst')
CMD_CASES_DIR = TEST_DATA_DIR.joinpath('command_test_cases')
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')
LIB_DIR = THIS_FILE.parents[2].joinpath('lib', 'cli_command_parser')


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
            RstWriter(tmp_path).document_scripts(EXAMPLES_DIR.glob('*.py'), 'examples', index_header='Example Scripts')

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
    def test_inherited_description_included(self):
        class Foo(Command, description='foobarbaz', show_inherited_descriptions=True):
            sub = SubCommand()

        class Bar(Foo):
            pass

        self.assertEqual(2, render_command_rst(Foo).count('\nfoobarbaz\n'))

    def test_unique_description_included(self):
        for show in (True, False):

            class Foo(Command, description='foobarbaz', show_inherited_descriptions=show):
                sub = SubCommand()

            class Bar(Foo, description='bazbarfoo'):
                pass

            rendered = render_command_rst(Foo)
            self.assertEqual(1, rendered.count('\nfoobarbaz\n'))
            self.assertEqual(1, rendered.count('\nbazbarfoo\n'))

    def test_basic_subcommand_no_help(self):
        expected = THIS_DATA_DIR.joinpath('basic_subcommand_no_help.rst').read_text('utf-8')

        class Base(Command, doc_name='basic_subcommand_no_help', prog='foo.py', show_docstring=False, add_help=False):
            sub_cmd = SubCommand()

        class Foo(Base):
            pass

        self.assert_strings_equal(expected, render_command_rst(Base, fix_name=False))

    def test_subcommand_script_name_matches_base(self):
        class DocWriter(Command, description='Doc writing tester'):
            @cached_property
            def rst_str(self):
                command = next(iter(load_commands(CMD_CASES_DIR.joinpath('sub_cmd_with_mid_abc.py')).values()))
                return render_command_rst(command, fix_name=False)

            def main(self):
                _ = self.rst_str

        expected = THIS_DATA_DIR.joinpath('sub_cmd_with_mid_abc.rst').read_text('utf-8')
        with patch('sys.argv', [__file__]):
            rendered = DocWriter.parse_and_run().rst_str

        self.assert_strings_equal(expected, rendered)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
