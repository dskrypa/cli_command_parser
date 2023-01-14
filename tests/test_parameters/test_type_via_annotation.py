#!/usr/bin/env python

import sys
from pathlib import Path
from typing import Optional, Collection, Sequence, Iterable, Union
from unittest import main, skipIf

from cli_command_parser import Command
from cli_command_parser.parameters import Positional, Option
from cli_command_parser.testing import ParserTest


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
