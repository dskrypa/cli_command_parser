#!/usr/bin/env python

from __future__ import annotations

import pickle
from contextlib import contextmanager, redirect_stdout
from typing import Type, Union
from unittest import TestCase, main
from unittest.mock import Mock, patch

from cli_command_parser import Command, Flag
from cli_command_parser.error_handling import (
    ErrorHandler,
    Handler,
    error_handler,
    extended_error_handler,
    no_exit_handler,
)
from cli_command_parser.error_handling.other import handle_kb_interrupt as handle_other_kbi
from cli_command_parser.exceptions import (
    CommandParserException,
    InvalidChoice,
    MultiParamUsageError,
    ParamConflict,
    ParamsMissing,
    ParamUsageError,
    ParserExit,
)
from cli_command_parser.testing import ParserTest, RedirectStreams

with patch('ctypes.WinDLL', create=True):
    from cli_command_parser.error_handling.windows import (
        handle_kb_interrupt as handle_win_kbi,
        handle_win_os_pipe_error,
    )

MODULE = 'cli_command_parser.error_handling'
WIN_MODULE = 'cli_command_parser.error_handling.windows'
OTHER_MODULE = 'cli_command_parser.error_handling.other'


class ErrorHandlingTest(TestCase):
    @contextmanager
    def assert_maybe_raises(self, exc_cls: Union[Type[BaseException], tuple[Type[BaseException], ...], None]):
        if exc_cls is None:
            yield
        else:
            with self.assertRaises(exc_cls):
                yield

    def test_error_handler_unregister(self):
        handler = ErrorHandler()
        handler.register(lambda e: None, ValueError)
        self.assertIn(ValueError, handler.exc_handler_map)
        handler.unregister(ValueError)
        handler.unregister(TypeError)
        self.assertNotIn(ValueError, handler.exc_handler_map)

    def test_error_handler_handle_subclass(self):
        class TestExc(ValueError):
            pass

        cases = [(None, TestExc), (False, TestExc), (True, None), (0, SystemExit), (1, SystemExit), ('foo', SystemExit)]
        for return_value, expected_exc in cases:
            with self.subTest(return_value=return_value, expected_exc=expected_exc):
                handler = ErrorHandler()
                mock = Mock(return_value=return_value)
                handler.register(mock, ValueError)
                with self.assert_maybe_raises(expected_exc):
                    with handler:
                        raise TestExc

                self.assertEqual(mock.call_count, 1)

    def test_error_handler_failure(self):
        handler = ErrorHandler()
        handler.register(Mock(return_value=False), ValueError)
        with self.assertRaises(ValueError):
            with handler:
                raise ValueError

    def test_handle_parser_exception(self):
        handler = ErrorHandler()
        with RedirectStreams() as streams, self.assertRaises(SystemExit), handler:
            raise CommandParserException('test one')

        self.assertEqual(streams.stderr, 'test one\n')

    def test_error_handler_repr(self):
        self.assertIn('handlers=', repr(ErrorHandler()))

    def test_most_specific_handler_chosen(self):
        handler = ErrorHandler()
        handler.register(lambda e: None, Exception)
        exc = ParamUsageError(Flag('--foo'), 'test')
        self.assertIs(CommandParserException.exit, next(handler.iter_handlers(ParamUsageError, exc)))

    def test_handler_equality(self):
        def foo(e):
            pass

        a = Handler(TypeError, foo)
        b = Handler(TypeError, foo)
        c = Handler(ValueError, foo)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_broken_pipe_caught(self):
        with RedirectStreams() as streams, error_handler:
            raise BrokenPipeError

        self.assertEqual('', streams.stdout)

    def test_handlers_are_inherited(self):
        self.assertNotIn(BrokenPipeError, ErrorHandler().exc_handler_map)
        self.assertIn(BrokenPipeError, error_handler.copy().exc_handler_map)  # -> _handle_broken_pipe


class TestCommandErrorHandling(TestCase):
    def test_no_error_handler_run(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            __call__ = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.__call__.called)

    def test_no_error_handler_main(self):
        class Foo(Command, error_handler=None):
            bar = Flag()
            main = Mock()

        Foo.parse_and_run([])
        self.assertTrue(Foo.main.called)

    def test_no_run_after_parse_error(self):
        class Foo(Command, error_handler=no_exit_handler):
            bar = Flag()
            __call__ = Mock()

        with RedirectStreams():
            Foo.parse_and_run(['-B'])

        self.assertFalse(Foo.__call__.called)

    def test_command_with_alt_error_handler_is_pickleable(self):
        foo = ExampleCommand.parse(['-h'])
        clone = pickle.loads(pickle.dumps(foo))
        self.assertIsNot(foo, clone)
        with RedirectStreams() as streams:
            clone()

        self.assertTrue(streams.stdout.startswith('usage: '))


class ExampleCommand(Command, error_handler=no_exit_handler):
    """
    This command needed to be defined here for it to be pickleable - pickle.dumps fails when the class is defined
    in a test method.
    """


class ExceptionTest(TestCase):
    def test_exit_str(self):
        self.assertIn('foo', str(ParserExit(message='foo')))
        self.assertNotIn('foo', str(ParserExit()))

    def test_exit_exit(self):
        with RedirectStreams() as streams, self.assertRaises(SystemExit):
            ParserExit(message='test').exit()

        self.assertIn('test', streams.stderr)

    def test_usage_error_str(self):
        self.assertEqual('test', str(ParamUsageError(None, 'test')))  # noqa
        param_str = str(ParamUsageError(Flag('--foo'), 'test'))
        self.assertTrue(param_str.startswith('argument'))
        self.assertTrue(param_str.endswith('test'))

    def test_multiple_invalid(self):
        self.assertIn("choices: 'a', 'b'", str(InvalidChoice(Flag('--foo'), ['a', 'b'], ['c', 'd'])))

    def test_conflict_no_message(self):
        exc = ParamConflict([Flag('-t')])
        self.assertNotIn('(', str(exc))

    def test_params_missing_no_message(self):
        exc = ParamsMissing([Flag('-t')])
        self.assertNotIn('(', str(exc))

    def test_params_missing_message(self):
        exc = ParamsMissing([Flag('-a'), Flag('-b')], 'test')
        self.assertTrue(str(exc).endswith('-a, -b (test)'))

    def test_multi_usage_error_message(self):
        exc = MultiParamUsageError([Flag('-a'), Flag('-b')], 'test')
        self.assertTrue(str(exc).endswith('combination of arguments: -a, -b (test)'))


win_error_handler = extended_error_handler.copy()
win_error_handler.register(handle_win_kbi, KeyboardInterrupt)


class WindowsErrorHandlingTest(ParserTest):
    def test_broken_pipe(self):
        self.assertIn(OSError, win_error_handler.exc_handler_map)
        self.assertEqual([handle_win_os_pipe_error], list(win_error_handler.iter_handlers(OSError, OSError())))

        with patch(f'{WIN_MODULE}.RtlGetLastNtStatus', return_value=0xC000_00B2):
            with self.assertRaises(OSError), win_error_handler:
                raise OSError(22, 'test')  # Another error won't be raised, so it needs to be caught again

    def test_broken_pipe_handled(self):
        mock = Mock(close=Mock(side_effect=OSError()))
        with patch(f'{WIN_MODULE}.RtlGetLastNtStatus', return_value=0xC000_00B1):  # STATUS_PIPE_CLOSING
            with redirect_stdout(mock), win_error_handler:
                raise OSError(22, 'test')

        self.assertTrue(mock.close.called)

    def test_oserror_other_ignored(self):
        with RedirectStreams(), self.assertRaises(OSError), win_error_handler:
            raise OSError(21, 'test')

    def test_keyboard_interrupt_print(self):
        with self.assert_raises_contains_str(SystemExit, '130'):
            with RedirectStreams() as streams, win_error_handler:
                raise KeyboardInterrupt

        self.assertEqual('\n', streams.stdout)

    def test_keyboard_interrupt_print_pipe_error(self):
        with patch(f'{WIN_MODULE}.print', side_effect=BrokenPipeError):
            with self.assert_raises_contains_str(SystemExit, '130'):
                with RedirectStreams() as streams, win_error_handler:
                    raise KeyboardInterrupt

        self.assertEqual('', streams.stdout)

    def test_keyboard_interrupt_print_os_error_broken_pipe(self):
        with patch(f'{WIN_MODULE}.print', side_effect=OSError):
            with patch(f'{WIN_MODULE}.handle_win_os_pipe_error', return_value=True):
                with self.assert_raises_contains_str(SystemExit, '130'):
                    with RedirectStreams() as streams, win_error_handler:
                        raise KeyboardInterrupt

        self.assertEqual('', streams.stdout)

    def test_keyboard_interrupt_print_os_error_other(self):
        with patch(f'{WIN_MODULE}.print', side_effect=OSError):
            with patch(f'{WIN_MODULE}.handle_win_os_pipe_error', return_value=False):
                with self.assertRaises(OSError), RedirectStreams() as streams, win_error_handler:
                    raise KeyboardInterrupt

        self.assertEqual('', streams.stdout)


other_error_handler = extended_error_handler.copy()
other_error_handler.register(handle_other_kbi, KeyboardInterrupt)


class OtherOSErrorHandlingTest(ParserTest):
    def test_keyboard_interrupt_print(self):
        with self.assert_raises_contains_str(SystemExit, '130'):
            with RedirectStreams() as streams, other_error_handler:
                raise KeyboardInterrupt

        self.assertEqual('\n', streams.stdout)

    def test_keyboard_interrupt_print_pipe_error(self):
        with patch(f'{OTHER_MODULE}.print', side_effect=BrokenPipeError):
            with self.assert_raises_contains_str(SystemExit, '130'):
                with RedirectStreams() as streams, other_error_handler:
                    raise KeyboardInterrupt

        self.assertEqual('', streams.stdout)


if __name__ == '__main__':
    main(verbosity=2)
