"""
Helpers for unit tests

:author: Doug Skrypa
"""

from typing import Any, Iterable, Type, Union
from unittest import TestCase

from .actions import help_action
from .commands import CommandType, Command
from .exceptions import UsageError

Argv = list[str]
Expected = dict[str, Any]
Case = tuple[Argv, Expected]
ExceptionCase = Union[tuple[Argv, Type[Exception]], tuple[Argv, Type[Exception], str]]


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
        parsed = cmd.parser.arg_dict(cmd.args, (help_action,))  # noqa
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

    def assert_parse_fails_cases(self, cmd_cls: CommandType, cases: Iterable[ExceptionCase], message: str = None):
        for case in cases:
            try:
                argv, exc, pat = case
            except ValueError:
                argv, exc = case
                pat = None

            with self.subTest(expected='exception', argv=argv):
                self.assert_parse_fails(cmd_cls, argv, exc, pat, message=message)
