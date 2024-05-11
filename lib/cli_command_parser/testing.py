"""
Helpers for unit tests

:author: Doug Skrypa
"""
# pylint: disable=R0913,C0103

from __future__ import annotations

import sys
from contextlib import AbstractContextManager, contextmanager
from difflib import unified_diff
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, TYPE_CHECKING, Any, Callable, ContextManager, Dict, Iterable, List, Tuple, Type, Union
from unittest import TestCase
from unittest.mock import Mock, patch, seal

from .commands import Command
from .context import Context
from .core import get_params
from .documentation import load_commands
from .exceptions import UsageError
from .parameters import help_action

if TYPE_CHECKING:
    from .typing import CommandCls, OptStr

__all__ = [
    'ParserTest',
    'RedirectStreams',
    'format_diff',
    'get_rst_text',
    'get_help_text',
    'get_usage_text',
    'sealed_mock',
    'load_command',
    'TemporaryDir',
]

Argv = List[str]
Expected = Dict[str, Any]
Kwargs = Dict[str, Any]
Env = Dict[str, str]
Case = Tuple[Argv, Expected]
EnvCase = Tuple[Argv, Env, Expected]
ExcType = Type[Exception]
ExceptionCase = Union[Argv, Tuple[Argv, ExcType], Tuple[Argv, ExcType, str]]
ExcCases = Iterable[ExceptionCase]
CallExceptionCase = Union[Tuple[Kwargs, ExcType], Tuple[Kwargs, ExcType, str]]
CallExceptionCases = Iterable[CallExceptionCase]

OPT_ENV_MOD = 'cli_command_parser.parser.environ'
EXCLUDE_ACTIONS = (help_action,)


class AssertRaisesWithStringContext:
    """
    Simplified version of the stdlib ``_AssertRaisesContext`` that tests whether the raised exception's string contains
    the given text rather than matching it against a regex pattern.  This avoids the regex overhead when it isn't
    necessary, which is the majority of the time for such checks in this project.
    """

    __slots__ = ('test_case', 'expected_exc', 'expected_text', 'msg')

    def __init__(self, test_case: TestCase, expected_exc: Type[BaseException], text: OptStr = None, msg: OptStr = None):
        self.test_case = test_case
        self.expected_exc = expected_exc
        self.expected_text = text
        self.msg = (' - ' + msg) if msg else ''

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.test_case.fail(f'{self.expected_exc.__name__} not raised{self.msg}')
        elif not issubclass(exc_type, self.expected_exc):
            return False  # Let unexpected exceptions be propagated
        elif self.expected_text and self.expected_text not in str(exc_val):
            self.test_case.fail(f'{self.expected_text!r} not found in {str(exc_val)!r}{self.msg}')
        return True


class ParserTest(TestCase):
    # def setUp(self):
    #     print()
    #
    # def subTest(self, *args, **kwargs):
    #     print()
    #     return super().subTest(*args, **kwargs)

    def assert_dict_equal(self, d1, d2, msg: str = None):
        self.assertIsInstance(d1, dict, 'First argument is not a dictionary')
        self.assertIsInstance(d2, dict, 'Second argument is not a dictionary')
        self._assert_dict_equal(d1, d2, msg)

    def _assert_dict_equal(self, d1, d2, msg: str = None):
        if d1 != d2:
            self.fail(self._formatMessage(msg, f'{d1} != {d2}\n{format_dict_diff(d1, d2)}'))

    def assert_raises_contains_str(self, expected_exc: Type[BaseException], expected_text: str, msg: str = None):
        return AssertRaisesWithStringContext(self, expected_exc, expected_text, msg)

    def assert_parse_results(self, cmd_cls: CommandCls, argv: Argv, expected: Expected, msg: str = None) -> Command:
        cmd = cmd_cls.parse(argv)
        self._assert_dict_equal(expected, cmd.ctx.get_parsed(cmd, exclude=EXCLUDE_ACTIONS), msg)
        return cmd

    def assert_parse_results_cases(self, cmd_cls: CommandCls, cases: Iterable[Case], msg: str = None):
        for argv, expected in cases:
            with self.subTest(expected='results', argv=argv):
                self.assert_parse_results(cmd_cls, argv, expected, msg)

    def assert_env_parse_results(
        self, cmd_cls: CommandCls, argv: Argv, env: Env, expected: Expected, msg: str = None
    ) -> Command:
        with patch(OPT_ENV_MOD, env):
            return self.assert_parse_results(cmd_cls, argv, expected, msg)

    def assert_env_parse_results_cases(self, cmd_cls: CommandCls, cases: Iterable[EnvCase], msg: str = None):
        for argv, env, expected in cases:
            with self.subTest(expected='results', argv=argv, env=env):
                self.assert_env_parse_results(cmd_cls, argv, env, expected, msg)

    def assert_parse_fails(
        self,
        cmd_cls: CommandCls,
        argv: Argv,
        expected_exc: ExcType = UsageError,
        expected_pattern: str = None,
        msg: str = None,
        regex: bool = False,
    ):
        if expected_pattern and regex:
            with self.assertRaisesRegex(expected_exc, expected_pattern, msg=msg):
                cmd_cls.parse(argv)
        else:
            with AssertRaisesWithStringContext(self, expected_exc, expected_pattern, msg):
                cmd_cls.parse(argv)

    def assert_parse_fails_cases(self, cmd_cls: CommandCls, cases: ExcCases, exc: ExcType = None, msg: str = None):
        for argv, exc, pat in _iter_exc_cases(cases, exc):
            with self.subTest(expected='exception', argv=argv):
                with AssertRaisesWithStringContext(self, exc, pat, msg):
                    cmd_cls.parse(argv)

    def assert_argv_parse_fails_cases(
        self, cmd_cls: CommandCls, cases: Iterable[Argv], exc: ExcType = UsageError, msg: str = None
    ):
        """Convenience method for calling :meth:`.assert_parse_fails_cases` with a default exception type."""
        self.assert_parse_fails_cases(cmd_cls, cases, exc, msg)

    def assert_call_fails(
        self,
        func: Callable,
        kwargs: Kwargs,
        exc: ExcType = Exception,
        expected_exc_msg: str = None,
        msg: str = None,
    ):
        with AssertRaisesWithStringContext(self, exc, expected_exc_msg, msg):
            func(**kwargs)

    def assert_call_fails_cases(self, func: Callable, cases: Iterable[CallExceptionCase], msg: str = None):
        for kwargs, exc, pat in _iter_exc_cases(cases):
            with self.subTest(expected='exception', kwargs=kwargs):
                with AssertRaisesWithStringContext(self, exc, pat, msg):
                    func(**kwargs)

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

    def assert_str_contains(self, sub_text: str, text: str, diff_lines: int = 3):
        if sub_text not in text:
            diff = format_diff(sub_text, text, n=diff_lines)
            self.fail('String did not contain expected text:\n' + diff)

    @contextmanager
    def env_vars(self, case: str, **env_vars):
        with self.subTest(case=case), patch(OPT_ENV_MOD, env_vars):
            yield


def _iter_exc_cases(cases: Union[ExcCases, CallExceptionCases], exc: ExcType = None):
    if exc is not None:
        for args in cases:
            yield args, exc, None
    else:
        for case in cases:
            try:
                args, exc = case
            except ValueError:
                yield case  # Assume it is a 3-tuple of ([argv|kwargs], exc, pattern)
            else:
                yield args, exc, None


# region Formatting


def _colored(text: str, color: int, end: str = '\n'):
    return f'\x1b[38;5;{color}m{text}\x1b[0m{end}'


def format_diff(a: str, b: str, name_a: str = 'expected', name_b: str = '  actual', n: int = 3) -> str:
    sio = StringIO()
    for i, line in enumerate(unified_diff(a.splitlines(), b.splitlines(), name_a, name_b, n=n, lineterm='')):
        if line.startswith('+') and i > 1:
            sio.write(_colored(line, 2))
        elif line.startswith('-') and i > 1:
            sio.write(_colored(line, 1))
        elif line.startswith('@@ '):
            sio.write(_colored(line, 6, '\n\n'))
        else:
            sio.write(line + '\n')

    return sio.getvalue()


def format_dict_diff(a: dict[str, Any], b: dict[str, Any]) -> str:
    formatted_a = []
    formatted_b = []
    for key in sorted(set(a) | set(b)):
        try:
            val_a = a[key]
        except KeyError:
            str_b = f'{key!r}: {b[key]!r}'
            formatted_a.append(' ' * len(str_b))
            formatted_b.append(_colored(str_b, 2, ''))
        else:
            str_a = f'{key!r}: {val_a!r}'
            try:
                val_b = b[key]
            except KeyError:
                str_b = ' ' * len(str_a)
                formatted_a.append(_colored(str_a, 1, ''))
                formatted_b.append(str_b)
            else:
                str_b = f'{key!r}: {val_b!r}'
                if val_a == val_b:
                    formatted_a.append(str_a)
                    formatted_b.append(str_b)
                else:
                    formatted_a.append(_colored(str_a, 2, ''))
                    formatted_b.append(_colored(str_b, 1, ''))

    return f'- {{{", ".join(formatted_a)}}}\n+ {{{", ".join(formatted_b)}}}'


# endregion


class RedirectStreams(AbstractContextManager):
    _stdin: Union[IO, str, bytes, None] = None

    def __init__(self, stdin: Union[IO, str, bytes, None] = None):
        self._old = {}
        if stdin is not None:
            if isinstance(stdin, bytes):
                self._stdin = BytesIO(stdin)
                self._stdin.buffer = self._stdin  # pretend to be the underlying buffer as well
            elif isinstance(stdin, str):
                self._stdin = StringIO(stdin)
                self._stdin.buffer = BytesIO(stdin.encode('utf-8'))
            else:
                self._stdin = stdin
        self._stdout = StringIO()
        self._stderr = StringIO()

    @property
    def stdout(self) -> str:
        return self._stdout.getvalue()

    @property
    def stderr(self) -> str:
        return self._stderr.getvalue()

    def __enter__(self) -> RedirectStreams:
        streams = {'stdout': self._stdout, 'stderr': self._stderr}
        if self._stdin is not None:
            streams['stdin'] = self._stdin
        for name, io in streams.items():
            self._old[name] = getattr(sys, name)
            setattr(sys, name, io)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        while self._old:
            name, orig = self._old.popitem()
            setattr(sys, name, orig)


# region Help / Usage / RST Text


def get_usage_text(cmd: Type[Command]) -> str:
    with cmd().ctx:
        return get_params(cmd).formatter.format_usage()


def get_help_text(cmd: Union[Type[Command], Command], terminal_width: int = 199) -> str:
    if not isinstance(cmd, Command):
        cmd = cmd()

    cmd.ctx._terminal_width = terminal_width
    with cmd.ctx:
        return get_params(cmd).formatter.format_help()


def get_rst_text(cmd: Union[Type[Command], Command]) -> str:
    if not isinstance(cmd, Command):
        cmd = cmd()

    cmd.ctx._terminal_width = 199
    with cmd.ctx:
        return get_params(cmd).formatter.format_rst()


# endregion


def sealed_mock(*args, **kwargs):
    kwargs.setdefault('return_value', None)
    mock = Mock(*args, **kwargs)
    seal(mock)
    return mock


@contextmanager
def load_command(directory: Path, name: str, cmd_name: str, **kwargs) -> ContextManager[CommandCls]:
    path = directory.joinpath(name)
    with Context.for_prog(path, **kwargs):
        yield load_commands(path)[cmd_name]


class TemporaryDir(TemporaryDirectory):
    def __enter__(self) -> Path:
        return Path(self.name)
