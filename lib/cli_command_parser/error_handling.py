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

import platform
import sys
from typing import Type, Callable, Union, Optional, Dict

from .exceptions import CommandParserException

__all__ = ['ErrorHandler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

WINDOWS = platform.system().lower() == 'windows'


class ErrorHandler:
    _exc_handler_map: Dict[Type[BaseException], Callable] = {}

    def __init__(self):
        self.exc_handler_map: Dict[Type[BaseException], Callable] = {}

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[handlers={len(self.exc_handler_map)}]>'

    def register(self, handler: Callable, *exceptions: Type[BaseException]):
        for exc in exceptions:
            self.exc_handler_map[exc] = handler

    def unregister(self, *exceptions):
        for exc in exceptions:
            try:
                del self.exc_handler_map[exc]
            except KeyError:
                pass

    def __call__(self, *exceptions: Type[BaseException]):
        def _handler(func: Union[Callable, staticmethod]):
            self.register(func, *exceptions)
            return func

        return _handler

    @classmethod
    def cls_handler(cls, *exceptions: Type[BaseException]):
        def _cls_handler(func: Union[Callable, staticmethod]):
            for exc in exceptions:
                cls._exc_handler_map[exc] = func
            return func

        return _cls_handler

    def get_handler(self, exc_type: Type[BaseException], exc: BaseException) -> Optional[Callable]:
        exc_handler_maps = (self.exc_handler_map, self._exc_handler_map)
        for exc_handler_map in exc_handler_maps:
            try:
                return exc_handler_map[exc_type]
            except KeyError:
                pass
        for exc_handler_map in exc_handler_maps:
            try:
                return next((f for ec, f in exc_handler_map.items() if isinstance(exc, ec)))
            except StopIteration:
                pass

        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb) -> bool:
        handler = self.get_handler(exc_type, exc_val)
        if handler:
            result = handler(exc_val)
            if result in (True, None):
                return True

        return False

    def copy(self) -> 'ErrorHandler':
        clone = self.__class__()
        clone.exc_handler_map.update(self.exc_handler_map)
        return clone


class NullErrorHandler:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


ErrorHandler.cls_handler(CommandParserException)(CommandParserException.exit)

error_handler = ErrorHandler()
error_handler.register(lambda e: print(), KeyboardInterrupt)
error_handler.register(lambda e: None, BrokenPipeError)

no_exit_handler = error_handler.copy()
no_exit_handler(CommandParserException)(CommandParserException.show)

extended_error_handler = error_handler.copy()

if WINDOWS:
    import ctypes

    RtlGetLastNtStatus = ctypes.WinDLL('ntdll').RtlGetLastNtStatus
    RtlGetLastNtStatus.restype = ctypes.c_ulong
    NT_STATUSES = {0xC000_00B1: 'STATUS_PIPE_CLOSING', 0xC000_014B: 'STATUS_PIPE_BROKEN'}

    @extended_error_handler(OSError)
    def _handle_os_error(exc: OSError):
        """
        This is a workaround for `issue35754 <https://bugs.python.org/issue35754>`_, which is a bug in the way that the
        windows error code for a broken pipe is translated into an errno value.  It should be translated to
        :data:`~errno.EPIPE`, but it uses :data:`~errno.EINVAL` (22) instead.

        Prevents the following when piping output to utilities such as ``| head``:
            Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
            OSError: [Errno 22] Invalid argument
        """
        if exc.errno == 22 and RtlGetLastNtStatus() in NT_STATUSES:
            try:
                sys.stdout.close()
            except OSError:
                pass
            return True

        return False
