#!/usr/bin/env python

from pathlib import Path
from unittest import main

from cli_command_parser.formatting.commands import get_formatter
from cli_command_parser.testing import ParserTest
from cli_command_parser.documentation import load_commands

THIS_FILE = Path(__file__).resolve()
EXAMPLES_DIR = THIS_FILE.parents[1].joinpath('examples')


class ExampleHelpTest(ParserTest):
    def test_advanced_subcommand(self):
        script_path = EXAMPLES_DIR.joinpath('advanced_subcommand.py')
        commands = load_commands(script_path)
        for args in ('foo', 'run foo'):
            expected = f'usage: advanced_subcommand.py {args} [--verbose [VERBOSE]] [--help]'
            with self.subTest(args=args):
                cmd = commands['Base'].parse(args.split())
                with cmd.ctx:
                    self.assert_str_starts_with_line(expected, get_formatter(cmd).format_help())


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
