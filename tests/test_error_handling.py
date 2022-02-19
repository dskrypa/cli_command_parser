#!/usr/bin/env python

from contextlib import redirect_stderr, redirect_stdout
from importlib import reload
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock, patch

import command_parser.error_handling
from command_parser.error_handling import ErrorHandler, extended_error_handler, _handle_os_error
from command_parser.exceptions import CommandParserException, ParserExit, ParamUsageError, InvalidChoice, ParamConflict
from command_parser.parameters import Flag


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
        sio = StringIO()
        with redirect_stderr(sio), self.assertRaises(SystemExit), handler:
            raise CommandParserException('test one')

        self.assertEqual(sio.getvalue(), 'test one\n')

    def test_broken_pipe(self):
        self.assertIn(OSError, extended_error_handler.exc_handler_map)
        handler = extended_error_handler.get_handler(OSError, OSError())
        self.assertEqual(handler, _handle_os_error)

        sio = StringIO()
        with redirect_stdout(sio), self.assertRaises(OSError), extended_error_handler:
            raise OSError(22, 'test')  # Another error won't be raised, so it needs to be caught again

        self.assertEqual(sio.getvalue(), '\n')

    def test_broken_pipe_handled(self):
        mock = Mock(write=Mock(side_effect=OSError()))
        with redirect_stdout(mock), extended_error_handler:
            raise OSError(22, 'test')

        self.assertTrue(mock.write.called)

    def test_oserror_other_ignored(self):
        with redirect_stdout(Mock()), self.assertRaises(OSError), extended_error_handler:
            raise OSError(21, 'test')

    def test_keyboard_interrupt_print(self):
        mock = Mock(write=Mock())
        with redirect_stdout(mock), extended_error_handler:
            raise KeyboardInterrupt

        self.assertEqual(mock.write.call_args.args[0], '\n')

    def test_broken_pipe_caught(self):
        mock = Mock(write=Mock())
        with redirect_stdout(mock), extended_error_handler:
            raise BrokenPipeError

        self.assertFalse(mock.write.called)


class ExceptionTest(TestCase):
    def test_exit_str(self):
        self.assertIn('foo', str(ParserExit(message='foo')))
        self.assertNotIn('foo', str(ParserExit()))

    def test_exit_exit(self):
        mock = Mock(write=Mock())
        with redirect_stderr(mock), self.assertRaises(SystemExit):
            ParserExit(message='test').exit()

        self.assertTrue(mock.write.called)

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


class ModuleLoadTest(TestCase):
    def test_error_handling_windows(self):
        with patch('platform.system', return_value='windows'):
            reload(command_parser.error_handling)

    def test_error_handling_linux(self):
        with patch('platform.system', return_value='linux'):
            reload(command_parser.error_handling)

    def test_error_handling_pytest(self):
        with patch('sys.argv', ['pytest']):
            reload(command_parser.error_handling)

    def test_error_handling_no_argv(self):
        with patch('sys.argv', []):
            reload(command_parser.error_handling)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
