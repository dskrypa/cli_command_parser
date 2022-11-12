#!/usr/bin/env python

from contextlib import redirect_stdout
from importlib import reload
from unittest import TestCase, main
from unittest.mock import Mock, patch

import cli_command_parser.error_handling
from cli_command_parser.error_handling import ErrorHandler, no_exit_handler
from cli_command_parser.exceptions import CommandParserException, ParserExit, ParamUsageError, InvalidChoice
from cli_command_parser.exceptions import ParamConflict, ParamsMissing, MultiParamUsageError
from cli_command_parser import Command, Flag
from cli_command_parser.testing import RedirectStreams


class ErrorHandlingTest(TestCase):
    def test_error_handler_unregister(self):
        handler = ErrorHandler()
        handler.register(lambda e: None, ValueError)
        self.assertIn(ValueError, handler.exc_handler_map)
        handler.unregister(ValueError)
        handler.unregister(TypeError)
        self.assertNotIn(ValueError, handler.exc_handler_map)

    def test_error_handler_handle_subclass(self):
        class TestError(ValueError):
            pass

        handler = ErrorHandler()
        for value in (None, True):
            mock = Mock(return_value=value)
            handler.register(mock, ValueError)
            with handler:
                raise TestError

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


with patch('platform.system', return_value='windows'), patch('ctypes.WinDLL', create=True):
    reload(cli_command_parser.error_handling)
    from cli_command_parser.error_handling import extended_error_handler, _handle_os_error

    class BrokenPipeHandlingTest(TestCase):
        def test_broken_pipe(self):
            self.assertIn(OSError, extended_error_handler.exc_handler_map)
            self.assertEqual(_handle_os_error, extended_error_handler.get_handler(OSError, OSError()))

            with patch('cli_command_parser.error_handling.RtlGetLastNtStatus', return_value=0xC000_00B2):
                with self.assertRaises(OSError), extended_error_handler:
                    raise OSError(22, 'test')  # Another error won't be raised, so it needs to be caught again

        def test_broken_pipe_handled(self):
            mock = Mock(close=Mock(side_effect=OSError()))
            with patch('cli_command_parser.error_handling.RtlGetLastNtStatus', return_value=0xC000_00B1):
                with redirect_stdout(mock), extended_error_handler:
                    raise OSError(22, 'test')

            self.assertTrue(mock.close.called)

        def test_oserror_other_ignored(self):
            with RedirectStreams(), self.assertRaises(OSError), extended_error_handler:
                raise OSError(21, 'test')

        def test_keyboard_interrupt_print(self):
            with RedirectStreams() as streams, extended_error_handler:
                raise KeyboardInterrupt

            self.assertEqual('\n', streams.stdout)

        def test_broken_pipe_caught(self):
            with RedirectStreams() as streams, extended_error_handler:
                raise BrokenPipeError

            self.assertEqual('', streams.stdout)


class ModuleLoadTest(TestCase):
    def test_error_handling_linux(self):
        # This is purely for branch coverage...
        with patch('platform.system', return_value='linux'):
            reload(cli_command_parser.error_handling)


if __name__ == '__main__':
    try:
        main(verbosity=2)
    except KeyboardInterrupt:
        print()
