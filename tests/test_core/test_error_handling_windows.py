#!/usr/bin/env python

from __future__ import annotations

import platform
from contextlib import ExitStack, redirect_stdout
from unittest import main
from unittest.mock import Mock, patch

from cli_command_parser.error_handling import extended_error_handler
from cli_command_parser.testing import ParserTest, RedirectStreams

MODULE = 'cli_command_parser.error_handling.windows'


with patch('ctypes.WinDLL', create=True):
    from cli_command_parser.error_handling.windows import handle_kb_interrupt, handle_win_os_pipe_error

    extended_error_handler = extended_error_handler.copy()  # Using a copy to
    if platform.system().lower() != 'windows':
        extended_error_handler.register(handle_kb_interrupt, KeyboardInterrupt)

    class WindowsErrorHandlingTest(ParserTest):
        @classmethod
        def tearDownClass(cls):
            super().tearDownClass()
            if platform.system().lower() != 'windows':
                from cli_command_parser.error_handling.base import extended_error_handler

                extended_error_handler.unregister(OSError)

        def test_broken_pipe(self):
            self.assertIn(OSError, extended_error_handler.exc_handler_map)
            self.assertEqual([handle_win_os_pipe_error], list(extended_error_handler.iter_handlers(OSError, OSError())))

            with patch(f'{MODULE}.RtlGetLastNtStatus', return_value=0xC000_00B2):
                with self.assertRaises(OSError), extended_error_handler:
                    raise OSError(22, 'test')  # Another error won't be raised, so it needs to be caught again

        def test_broken_pipe_handled(self):
            mock = Mock(close=Mock(side_effect=OSError()))
            with patch(f'{MODULE}.RtlGetLastNtStatus', return_value=0xC000_00B1):
                with redirect_stdout(mock), extended_error_handler:
                    raise OSError(22, 'test')

            self.assertTrue(mock.close.called)

        def test_oserror_other_ignored(self):
            with RedirectStreams(), self.assertRaises(OSError), extended_error_handler:
                raise OSError(21, 'test')

        def test_keyboard_interrupt_print(self):
            with self.assert_raises_contains_str(SystemExit, '130'):
                with RedirectStreams() as streams, extended_error_handler:
                    raise KeyboardInterrupt

            self.assertEqual('\n', streams.stdout)

        def test_keyboard_interrupt_print_pipe_error(self):
            with ExitStack() as stack:
                stack.enter_context(patch(f'{MODULE}.print', side_effect=BrokenPipeError))
                stack.enter_context(self.assert_raises_contains_str(SystemExit, '130'))
                streams = stack.enter_context(RedirectStreams())
                stack.enter_context(extended_error_handler)
                raise KeyboardInterrupt

            self.assertEqual('', streams.stdout)  # noqa

        def test_keyboard_interrupt_print_os_error_broken_pipe(self):
            with ExitStack() as stack:
                stack.enter_context(patch(f'{MODULE}.print', side_effect=OSError))
                stack.enter_context(patch(f'{MODULE}.handle_win_os_pipe_error', return_value=True))
                stack.enter_context(self.assert_raises_contains_str(SystemExit, '130'))
                streams = stack.enter_context(RedirectStreams())
                stack.enter_context(extended_error_handler)
                raise KeyboardInterrupt

            self.assertEqual('', streams.stdout)  # noqa

        def test_keyboard_interrupt_print_os_error_other(self):
            with ExitStack() as stack:
                stack.enter_context(patch(f'{MODULE}.print', side_effect=OSError))
                stack.enter_context(patch(f'{MODULE}.handle_win_os_pipe_error', return_value=False))
                stack.enter_context(self.assertRaises(OSError))
                streams = stack.enter_context(RedirectStreams())
                stack.enter_context(extended_error_handler)
                raise KeyboardInterrupt

            self.assertEqual('', streams.stdout)  # noqa

        def test_broken_pipe_caught(self):
            with RedirectStreams() as streams, extended_error_handler:
                raise BrokenPipeError

            self.assertEqual('', streams.stdout)


if __name__ == '__main__':
    main(verbosity=2)
