#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser.documentation import load_commands
from cli_command_parser.testing import ParserTest, get_help_text

THIS_FILE = Path(__file__).resolve()
EXAMPLES_DIR = THIS_FILE.parents[2].joinpath('examples')
TEST_DATA_DIR = THIS_FILE.parents[1].joinpath('data', 'test_examples_documentation')


def load_example_command(name: str, cmd_name: str):
    return load_commands(EXAMPLES_DIR.joinpath(name))[cmd_name]


def load_expected(name: str) -> str:
    return TEST_DATA_DIR.joinpath(name).read_text('utf-8').rstrip()


class ExampleHelpTest(ParserTest):
    def test_advanced_subcommand(self):
        Base = load_example_command('advanced_subcommand.py', 'Base')
        for args in ('foo', 'run foo'):
            expected = f'usage: advanced_subcommand.py {args} [--verbose [VERBOSE]] [--help]'
            with self.subTest(args=args):
                self.assert_str_starts_with_line(expected, get_help_text(Base.parse(args.split())))

    def test_common_group_shown(self):
        ApiWrapper = load_example_command('rest_api_wrapper.py', 'ApiWrapper')
        for sub_cmd in ('show', 'find'):
            expected = load_expected(f'rest_api_wrapper__{sub_cmd}.txt')
            with self.subTest(sub_cmd=sub_cmd):
                cmd = ApiWrapper.parse([sub_cmd, '-h'])
                self.assert_strings_equal(expected, get_help_text(cmd).rstrip())

    def test_example_help_texts(self):
        cases = [
            ('echo.py', 'Echo', 'echo_help.txt'),
            ('simple_flags.py', 'Example', 'simple_flags_help.txt'),
            ('custom_inputs.py', 'InputsExample', 'custom_inputs_help.txt'),
            ('complex', 'Update', 'complex_update_help.txt'),
        ]
        for file_name, cmd_name, expected_file_name in cases:
            with self.subTest(file=file_name, command=cmd_name):
                command = load_example_command(file_name, cmd_name)
                expected = load_expected(expected_file_name)
                self.assert_strings_equal(expected, get_help_text(command()).rstrip())


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
