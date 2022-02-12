#!/usr/bin/env python

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import TestCase, main
from unittest.mock import Mock

from command_parser.error_handling import ErrorHandler, extended_error_handler, _handle_os_error
from command_parser.exceptions import CommandParserException, ParserExit, ParamUsageError, InvalidChoice
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
        with redirect_stderr(sio), handler:
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


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(warnings='ignore', verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()