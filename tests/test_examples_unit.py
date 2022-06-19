#!/usr/bin/env python

import sys
from pathlib import Path
from unittest import main, TestCase

from cli_command_parser.formatting.commands import get_formatter
from cli_command_parser.testing import RedirectStreams
from cli_command_parser.context import get_or_create_context

sys.path.append(Path(__file__).resolve().parents[1].joinpath('examples').as_posix())

from custom_inputs import InputsExample
from echo import Echo
from hello_world import HelloWorld


class ExampleHelpTest(TestCase):
    def test_echo_help(self):
        with get_or_create_context(Echo, terminal_width=199):
            cmd = Echo()
            self.assertIn('Write all of the provided arguments to stdout', get_formatter(cmd).format_help())

    def test_echo_main(self):
        with RedirectStreams() as streams:
            Echo.parse_and_run(['test', 'one'])
        self.assertEqual('test one\n', streams.stdout)

    def test_hello_default(self):
        with RedirectStreams() as streams:
            HelloWorld.parse_and_run([])
        self.assertEqual('Hello World!\n', streams.stdout)
        self.assertEqual('', streams.stderr)

    def test_hello_test(self):
        with RedirectStreams() as streams:
            HelloWorld.parse_and_run(['-n', 'test'])
        self.assertEqual('Hello test!\n', streams.stdout)

    def test_custom_input_json_stdin(self):
        with RedirectStreams('{"a": 1, "b": 2}') as streams:
            InputsExample.parse_and_run(['-j', '-'])
        self.assertEqual("You provided a dict\n[0] ('a', 1)\n[1] ('b', 2)\n", streams.stdout)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
