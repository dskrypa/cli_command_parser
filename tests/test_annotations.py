#!/usr/bin/env python

from contextlib import contextmanager
from pathlib import Path
from unittest import main
from unittest.mock import Mock, patch

from cli_command_parser import Context, inputs
from cli_command_parser.annotations import get_args
from cli_command_parser.documentation import load_commands
from cli_command_parser.testing import ParserTest

THIS_FILE = Path(__file__).resolve()
TEST_DATA_DIR = THIS_FILE.parent.joinpath('data', 'command_test_cases')


@contextmanager
def load_command(name: str, cmd_name: str):
    path = TEST_DATA_DIR.joinpath(name)
    with Context.for_prog(path):
        yield load_commands(path)[cmd_name]


class AnnotationsTest(ParserTest):
    def test_get_args(self):
        # This is for coverage in 3.9+ for the get_args compatibility wrapper, to mock the attr present in 3.8 & below
        self.assertEqual((), get_args(Mock(_special=True)))

    def test_annotation_using_forward_ref(self):
        with load_command('annotation_using_forward_ref.py', 'AnnotatedCommand') as AnnotatedCommand:
            self.assertIs(None, AnnotatedCommand.paths_a.type)
            self.assertIsInstance(AnnotatedCommand.paths_b.type, inputs.Path)

    def test_future_annotation_using_forward_ref(self):
        with load_command('future_annotation_using_forward_ref.py', 'AnnotatedCommand') as AnnotatedCommand:
            self.assertIs(None, AnnotatedCommand.paths_a.type)
            self.assertIsInstance(AnnotatedCommand.paths_b.type, inputs.Path)


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
