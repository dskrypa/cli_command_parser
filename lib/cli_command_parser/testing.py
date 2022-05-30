"""
Helpers for unit tests

:author: Doug Skrypa
"""

from difflib import unified_diff
from io import StringIO
from typing import Any, Iterable, Type, Union, Callable, Dict, List, Tuple
from unittest import TestCase

from .actions import help_action
from .commands import Command
from .core import CommandType
from .exceptions import UsageError

__all__ = ['ParserTest']

Argv = List[str]
Expected = Dict[str, Any]
Kwargs = Dict[str, Any]
Case = Tuple[Argv, Expected]
ExceptionCase = Union[Argv, Tuple[Argv, Type[Exception]], Tuple[Argv, Type[Exception], str]]
CallExceptionCase = Union[Tuple[Kwargs, Type[Exception]], Tuple[Kwargs, Type[Exception], str]]


class ParserTest(TestCase):
    # def setUp(self):
    #     print()
    #
    # def subTest(self, *args, **kwargs):
    #     print()
    #     return super().subTest(*args, **kwargs)

    def assert_parse_results(
        self, cmd_cls: CommandType, argv: Argv, expected: Expected, message: str = None
    ) -> Command:
        cmd = cmd_cls.parse_and_run(argv)
        parsed = cmd.ctx.get_parsed((help_action,))
        self.assertDictEqual(expected, parsed, message)
        return cmd

    def assert_parse_results_cases(self, cmd_cls: CommandType, cases: Iterable[Case], message: str = None):
        for argv, expected in cases:
            with self.subTest(expected='results', argv=argv):
                self.assert_parse_results(cmd_cls, argv, expected, message)

    def assert_parse_fails(
        self,
        cmd_cls: CommandType,
        argv: Argv,
        expected_exc: Type[Exception] = UsageError,
        expected_pattern: str = None,
        message: str = None,
    ):
        if expected_pattern:
            with self.assertRaisesRegex(expected_exc, expected_pattern, msg=message):
                cmd_cls.parse(argv)
        else:
            with self.assertRaises(expected_exc, msg=message):
                cmd_cls.parse(argv)

    def assert_parse_fails_cases(
        self, cmd_cls: CommandType, cases: Iterable[ExceptionCase], exc: Type[Exception] = None, message: str = None
    ):
        if exc is not None:
            for argv in cases:
                with self.subTest(expected='exception', argv=argv):
                    self.assert_parse_fails(cmd_cls, argv, exc, message=message)
        else:
            for case in cases:
                try:
                    argv, exc = case
                except ValueError:
                    argv, exc, pat = case
                else:
                    pat = None

                with self.subTest(expected='exception', argv=argv):
                    self.assert_parse_fails(cmd_cls, argv, exc, pat, message=message)

    def assert_call_fails(
        self,
        func: Callable,
        kwargs: Kwargs,
        exc: Type[Exception] = Exception,
        pattern: str = None,
        message: str = None,
    ):
        if pattern:
            with self.assertRaisesRegex(exc, pattern, msg=message):
                func(**kwargs)
        else:
            with self.assertRaises(exc, msg=message):
                func(**kwargs)

    def assert_call_fails_cases(self, func: Callable, cases: Iterable[CallExceptionCase], message: str = None):
        for case in cases:
            try:
                kwargs, exc = case
            except ValueError:
                kwargs, exc, pat = case
            else:
                pat = None

            with self.subTest(expected='exception', kwargs=kwargs):
                self.assert_call_fails(func, kwargs, exc, pat, message=message)

    def assert_strings_equal(
        self, expected: str, actual: str, message: str = None, diff_lines: int = 3, trim: bool = False
    ):
        if trim:
            expected = expected.rstrip()
            actual = '\n'.join(line.rstrip() for line in actual.splitlines())
        if message:
            self.assertEqual(expected, actual, message)
        elif expected != actual:
            diff = format_diff(expected, actual, n=diff_lines)
            # if not diff.strip():
            #     self.assertEqual(expected, actual)
            # else:
            self.fail('Strings did not match:\n' + diff)

    def assert_str_starts_with_line(self, prefix: str, text: str):
        new_line = text.index('\n')
        self.assertEqual(prefix, text[:new_line])


def _colored(text: str, color: int, end: str = '\n'):
    return f'\x1b[38;5;{color}m{text}\x1b[0m{end}'


def format_diff(a: str, b: str, name_a: str = 'expected', name_b: str = '  actual', n: int = 3) -> str:
    sio = StringIO()
    a = a.splitlines()
    b = b.splitlines()
    for i, line in enumerate(unified_diff(a, b, name_a, name_b, n=n, lineterm='')):
        if line.startswith('+') and i > 1:
            sio.write(_colored(line, 2))
        elif line.startswith('-') and i > 1:
            sio.write(_colored(line, 1))
        elif line.startswith('@@ '):
            sio.write(_colored(line, 6, '\n\n'))
        else:
            sio.write(line + '\n')

    return sio.getvalue()
