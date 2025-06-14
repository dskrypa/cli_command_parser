#!/usr/bin/env python

import sys
from abc import ABC
from inspect import getfile
from pathlib import Path
from unittest import main

from cli_command_parser import Command, Option
from cli_command_parser.config import OptionNameMode
from cli_command_parser.core import get_config
from cli_command_parser.documentation import (
    _module_name,
    _render_commands_rst,
    filtered_commands,
    import_module,
    load_commands,
    top_level_commands,
)
from cli_command_parser.testing import ParserTest
from cli_command_parser.typing import CommandCls

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data')
THIS_DATA_DIR = TEST_DATA_DIR.joinpath('test_documentation_utils')
CMD_CASES_DIR = TEST_DATA_DIR.joinpath('command_test_cases')
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')


class DocumentationUtilsTest(ParserTest):
    def test_filter_multiple_top_cmds(self):
        class Foo(Command):
            pass

        class Bar(Command):
            pass

        commands = {'Foo': Foo, 'Bar': Bar}
        self.assertEqual(commands, top_level_commands(commands))

    def test_filter_out_abc_parent(self):
        class Foo(Command, ABC):
            opt = Option()

        class Bar(Foo):
            pass

        self.assert_dict_equal({'Bar': Bar}, filtered_commands({'Foo': Foo, 'Bar': Bar}))

    def test_multi_command_rst(self):
        expected = THIS_DATA_DIR.joinpath('basic_command_multi.rst').read_text('utf-8')

        class Foo(Command, doc_name='basic_command_multi', prog='foo.py', show_docstring=False):
            pass

        class Bar(Command, doc_name='basic_command_multi', prog='foo.py', show_docstring=False):
            pass

        commands = {'Foo': Foo, 'Bar': Bar}
        self.assert_strings_equal(expected, _render_commands_rst(commands, fix_name=False), trim=True)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            import_module(CMD_CASES_DIR.joinpath('non_existant_file.py'))

    def test_import_error(self):
        with self.assertRaises(ImportError):  # Ensure this is raised for non-py files and similar
            import_module(THIS_DATA_DIR.joinpath('basic_command_multi.rst'))

    def test_remove_from_sys_modules_on_error(self):
        with self.assertRaises(RuntimeError):
            import_module(CMD_CASES_DIR.joinpath('runtime_error.py'))
        self.assertNotIn('runtime_error', sys.modules)

    def test_import_package(self):
        package = import_module(EXAMPLES_DIR.joinpath('complex'))
        expected = {'Example', 'HelloWorld', 'Logs', 'main'}
        self.assertSetEqual(expected, expected.intersection(dir(package)))

    def test_loaded_command_option_name_mode(self):
        commands = load_commands(TEST_DATA_DIR.joinpath('command_test_cases', 'opt_name_mode.py'))
        Base: CommandCls = commands['Base']
        Foo: CommandCls = commands['Foo']
        self.assertEqual(OptionNameMode.DASH, get_config(Base).option_name_mode)
        self.assertEqual(OptionNameMode.DASH, get_config(Foo).option_name_mode)
        self.assertEqual(['--a-b'], Foo.a_b.option_strs.long)
        self.assertEqual(['--a-b'], Foo.a_b.option_strs.display_long)
        self.assertEqual(['--a-c'], Foo.a_c.option_strs.display_long_primary)
        self.assertEqual(['--no-a-c'], Foo.a_c.option_strs.display_long_alt)

    def test_module_name(self):
        doc_module_path = Path(getfile(_module_name))
        with self.subTest('module'):
            self.assertEqual('cli_command_parser.documentation', _module_name(doc_module_path))

        with self.subTest('package'):
            params_pkg_path = doc_module_path.parent.joinpath('parameters', '__init__.py')
            self.assertEqual('cli_command_parser.parameters', _module_name(params_pkg_path))


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
