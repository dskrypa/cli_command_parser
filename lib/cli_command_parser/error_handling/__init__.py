"""
Error handling for expected / unexpected exceptions.

The default handler will...

- Call ``print()`` after catching a :class:`python:KeyboardInterrupt`, before exiting
- Exit gracefully after catching a :class:`python:BrokenPipeError` (often caused by piping output to a tool like
  ``tail``)

.. note::
    Parameters defined in a base Command will be processed in the context of that Command.  I.e., if a valid
    subcommand argument was provided, but an Option defined in the parent Command has an invalid value, then the
    exception that is raised about that invalid value will be raised before transferring control to the
    subcommand's error handler.

:author: Doug Skrypa
"""

from platform import system as _system

from .base import (
    ErrorHandler,
    Handler,
    HandlerFunc,
    NullErrorHandler,
    error_handler,
    extended_error_handler,
    no_exit_handler,
)

if _system().lower() == 'windows':
    from .windows import handle_kb_interrupt
else:
    from .other import handle_kb_interrupt

__all__ = ['ErrorHandler', 'Handler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

error_handler.register(handle_kb_interrupt, KeyboardInterrupt)
