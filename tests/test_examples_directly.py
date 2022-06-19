#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser.formatting.commands import get_formatter
from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import load_commands

THIS_FILE = Path(__file__).resolve()
EXAMPLES_DIR = THIS_FILE.parents[1].joinpath('examples')
TEST_DATA_DIR = THIS_FILE.parent.joinpath('data', 'test_examples_directly')


def load_example_command(name: str, cmd_name: str):
    return load_commands(EXAMPLES_DIR.joinpath(name))[cmd_name]


def load_expected(name: str) -> str:
    return TEST_DATA_DIR.joinpath(name).read_text('utf-8')


class ExampleHelpTest(ParserTest):
    def test_advanced_subcommand(self):
        Base = load_example_command('advanced_subcommand.py', 'Base')
        for args in ('foo', 'run foo'):
            expected = f'usage: advanced_subcommand.py {args} [--verbose [VERBOSE]] [--help]'
            with self.subTest(args=args):
                cmd = Base.parse(args.split())
                with cmd.ctx:
                    self.assert_str_starts_with_line(expected, get_formatter(cmd).format_help())

    def test_common_group_shown(self):
        ApiWrapper = load_example_command('rest_api_wrapper.py', 'ApiWrapper')
        for sub_cmd in ('show', 'find'):
            expected = load_expected(f'rest_api_wrapper__{sub_cmd}.txt')
            with self.subTest(sub_cmd=sub_cmd):
                cmd = ApiWrapper.parse([sub_cmd, '-h'])
                cmd.ctx._terminal_width = 199
                with cmd.ctx:
                    self.assert_strings_equal(expected, get_formatter(cmd).format_help())

    def test_echo_help(self):
        Echo = load_example_command('echo.py', 'Echo')
        expected = load_expected('echo_help.txt')
        cmd = Echo()
        cmd.ctx._terminal_width = 199
        with cmd.ctx:
            self.assert_strings_equal(expected, get_formatter(cmd).format_help())


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
