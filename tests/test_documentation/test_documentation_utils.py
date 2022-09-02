#!/usr/bin/env python

import sys
from pathlib import Path
from unittest import main

from cli_command_parser import Command
from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import top_level_commands, _render_commands_rst, import_module

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data', 'test_rst')
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')


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

    def test_import_package(self):
        package = import_module(EXAMPLES_DIR.joinpath('complex'))
        expected = {'Example', 'HelloWorld', 'Logs', 'main'}
        self.assertSetEqual(expected, expected.intersection(dir(package)))


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
