Error Handling
**************

Error handler functions can be registered to automatically handle exceptions that were not caught inside Commands.  The
error handler that should be used for a given Command can be specified through :class:`.CommandConfig` or, more
easily, through the :ref:`error_handler class keyword argument<configuration:Error Handling Options>` when defining
a Command.

All :class:`ErrorHandlers<.ErrorHandler>` will catch :class:`.CommandParserException` exceptions and handle them by
calling the exception's :meth:`~.CommandParserException.exit` method.

There are three ErrorHandler instances included by default:

    1. :obj:`~.error_handling.error_handler`:
        - Catches :class:`python:KeyboardInterrupt` and calls :func:`python:print`
        - Catches :class:`python:BrokenPipeError` and takes no further action (it prevents a stack trace from being
          printed for it)

    1. :obj:`~.error_handling.extended_error_handler`:
        - The default error handler
        - Handles everything that :obj:`~.error_handling.error_handler` does
        - The only difference between this handler and :obj:`~.error_handling.error_handler` is that an additional
          handler is registered only when running on Windows to catch :class:`python:OSError` and work around a bug
          related to the broken pipe error number: :func:`~.error_handling.handle_win_os_pipe_error`

    1. :obj:`~.error_handling.no_exit_handler`:
        - Overrides the :class:`.CommandParserException` exception handler to call the exception's
          :meth:`~.CommandParserException.show` method instead of :meth:`~.CommandParserException.exit`.


Configuration
=============

Example of how to use :obj:`~.error_handling.error_handler` instead of :obj:`~.error_handling.extended_error_handler`::

    from cli_command_parser import Command, Option, error_handler

    class MyCommand(Command, error_handler=error_handler):
        foo = Option()


Example of how to disable all error handling, including the handler for :class:`.CommandParserException`::

    from cli_command_parser import Command, Option

    class MyCommand(Command, error_handler=None):
        foo = Option()


Defining Error Handlers
=======================

To define an error handler function for an additional exception class, the :class:`.ErrorHandler` object can be used
as a decorator on the function that will handle the exception.

Similar to :meth:`python:object.__exit__`, if the error handler function returns a truthy value, then the exception
will be considered handled.  Behavior differs in the case of ``0``, which will be treated as a value with which
:func:`python:sys.exit` should be called.  In fact, :func:`python:sys.exit` will be called with any truthy value other
than ``True`` that is returned by the error handler function.

To indicate that the error was not handled, and that any other (less specific) error handlers that may match the
exception should be tried, the handler function should return ``False`` or any other falsey value (other than ``0``).

Alternatively, the handler function may call :func:`python:sys.exit` directly, if desired.  Similar to ``__exit__``,
the exception that was passed to the handler function should NOT be re-raised by the handler function.

If no handler function can be found for a given exception, or if none of them indicate that the exception was handled
or should result in a call to :func:`python:sys.exit`, then the exception will be propagated as usual (which should
result in the traceback being printed by the interpreter).

Example of adding a handler for a custom ``MyException`` exception to the default
:obj:`~.error_handling.extended_error_handler`::

    import sys
    from cli_command_parser import extended_error_handler

    @extended_error_handler(MyException)
    def handle_my_exception(exc: MyException):
        print(f'Unable to proceed due to {exc}', file=sys.stderr)
        return 1


Advanced
========

For repos that contain many separate entry points defined in a ``cli`` package or similar, a common error handler
function can be defined / registered in the package's ``__init__.py``.  This will result in that handler function being
used automatically for all of the modules within that package (and its sub-packages) without needing to explicitly
import it in any of them.

One example use case for that approach would be for user-facing scripts to have a catch-all handler registered for
``Exception``, where the handler logs just the error message by default, and only logs the full traceback when the user
specified ``--verbose`` output or similar.
