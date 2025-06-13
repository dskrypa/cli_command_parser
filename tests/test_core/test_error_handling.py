#!/usr/bin/env python

from __future__ import annotations

import pickle
from contextlib import contextmanager
from typing import Type, Union
from unittest import TestCase, main
from unittest.mock import Mock

from cli_command_parser import Command, Flag
from cli_command_parser.error_handling import ErrorHandler, Handler, no_exit_handler
from cli_command_parser.exceptions import (
    CommandParserException,
    InvalidChoice,
    MultiParamUsageError,
    ParamConflict,
    ParamsMissing,
    ParamUsageError,
    ParserExit,
)
from cli_command_parser.testing import RedirectStreams

MODULE = 'cli_command_parser.error_handling'


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


if __name__ == '__main__':
    main(verbosity=2)
