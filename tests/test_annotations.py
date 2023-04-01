#!/usr/bin/env python

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import main, skipIf
from unittest.mock import Mock

from cli_command_parser import Command, Context, Positional, Option, inputs
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


class TypeCastTest(ParserTest):
    def test_type_cast_singles(self):
        cases = [
            (int, '5', 5),
            (Optional[int], '5', 5),
            (Union[int], '5', 5),  # results in just int
            (Union[int, str], '5', '5'),
            (Union[int, str, None], '5', '5'),
            (_C, '5', _C('5')),
            (Union[int, _C], '5', '5'),
            (_resolved_path, 'test_parameters.py', 'test_parameters.py'),  # Not a proper annotation
            (Optional[_resolved_path], 'test_parameters.py', 'test_parameters.py'),  # Not a proper annotation
        ]
        for annotation, arg, expected in cases:
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Positional()

                self.assertEqual(expected, Foo.parse([arg]).bar)

    @skipIf(sys.version_info < (3, 9), 'stdlib collections are not subscriptable for annotations before 3.9')
    def test_type_cast_multiples_39(self):
        cases = [
            (list[int], ['1', '2'], [1, 2]),
            (list[Optional[int]], ['1', '2'], [1, 2]),
            (Optional[list[int]], ['1', '2'], [1, 2]),
            (tuple[int, ...], ['1', '2'], [1, 2]),
            (tuple[int, int], ['1', '2'], [1, 2]),
            (Sequence[int], ['1', '2'], [1, 2]),
            (Collection[int], ['1', '2'], [1, 2]),
            (Iterable[int], ['1', '2'], [1, 2]),
            (list[_C], ['1', '2'], [_C('1'), _C('2')]),
            (list, ['12', '3'], [['1', '2'], ['3']]),
            (list[Union[int, str, None]], ['12', '3'], ['12', '3']),
            (tuple[int, str, None], ['12', '3'], ['12', '3']),
            (list[_resolved_path], ['test_parser.py', 'test_commands.py'], ['test_parser.py', 'test_commands.py']),
            (dict[str, int, str], ['1', '2'], ['1', '2']),  # Not really a valid annotation, but it hits a branch
            (list[str, int, str], ['1', '2'], ['1', '2']),  # Not really a valid annotation, but it hits a branch
        ]
        for annotation, argv, expected in cases:
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Positional(nargs='+')

                self.assertEqual(expected, Foo.parse(argv).bar)

    def test_type_cast_multiples(self):
        from typing import List, Tuple

        cases = [
            (List[int], ['1', '2'], [1, 2]),
            (List[Optional[int]], ['1', '2'], [1, 2]),
            (Optional[List[int]], ['1', '2'], [1, 2]),
            (Tuple[int, ...], ['1', '2'], [1, 2]),
            (Tuple[int, int], ['1', '2'], [1, 2]),
            (Sequence[int], ['1', '2'], [1, 2]),
            (Collection[int], ['1', '2'], [1, 2]),
            (Iterable[int], ['1', '2'], [1, 2]),
            (List[_C], ['1', '2'], [_C('1'), _C('2')]),
            (List, ['12', '3'], [['1', '2'], ['3']]),
            (List[Union[int, str, None]], ['12', '3'], ['12', '3']),
            (Tuple[int, str, None], ['12', '3'], ['12', '3']),
            (List[_resolved_path], ['test_parser.py', 'test_commands.py'], ['test_parser.py', 'test_commands.py']),
        ]
        for annotation, argv, expected in cases:
            with self.subTest(annotation=annotation):

                class Foo(Command):
                    bar: annotation = Positional(nargs='+')

                self.assertEqual(expected, Foo.parse(argv).bar)

    def test_type_overrules_annotation(self):
        cases = [(str, int, ['--bar', '5'], 5), (int, str, ['--bar', '5'], '5')]
        for annotation, type_val, argv, expected in cases:

            class Foo(Command):
                bar: annotation = Option(type=type_val)

            self.assertEqual(expected, Foo.parse(argv).bar)


def _resolved_path(path):
    return Path(path).resolve()


class _C:
    def __init__(self, x: str):
        self.x = x

    def __eq__(self, other):
        return other.x == self.x


if __name__ == '__main__':
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
