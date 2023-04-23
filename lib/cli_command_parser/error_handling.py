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

from __future__ import annotations

import platform
import sys
from collections import ChainMap
from typing import Type, Callable, Union, Optional, Dict

from .exceptions import CommandParserException

__all__ = ['ErrorHandler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

WINDOWS = platform.system().lower() == 'windows'
HandlerFunc = Callable[[BaseException], Optional[bool]]


class ErrorHandler:
    __slots__ = ('exc_handler_map',)
    _exc_handler_map: Dict[Type[BaseException], Handler] = {}
    exc_handler_map: Dict[Type[BaseException], Handler]

    def __init__(self):
        self.exc_handler_map = {}

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[handlers={len(self.exc_handler_map)}]>'

    def register(self, handler: HandlerFunc, *exceptions: Type[BaseException]):
        for exc in exceptions:
            self.exc_handler_map[exc] = Handler(exc, handler)

    def unregister(self, *exceptions: Type[BaseException]):
        for exc in exceptions:
            try:
                del self.exc_handler_map[exc]
            except KeyError:
                pass

    def __call__(self, *exceptions: Type[BaseException]):
        def _handler(handler: Union[HandlerFunc, staticmethod]):
            self.register(handler, *exceptions)
            return handler

        return _handler

    @classmethod
    def cls_handler(cls, *exceptions: Type[BaseException]):
        def _cls_handler(handler: Union[HandlerFunc, staticmethod]):
            for exc in exceptions:
                cls._exc_handler_map[exc] = Handler(exc, handler)
            return handler

        return _cls_handler

    def get_handler(self, exc_type: Type[BaseException], exc: BaseException) -> Optional[HandlerFunc]:
        exc_handler_map = ChainMap(self.exc_handler_map, self._exc_handler_map)
        try:
            return exc_handler_map[exc_type].handler
        except KeyError:
            pass
        candidates = sorted(handler for ec, handler in exc_handler_map.items() if isinstance(exc, ec))
        try:
            return candidates[0].handler
        except IndexError:
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

    def copy(self) -> ErrorHandler:
        clone = self.__class__()
        clone.exc_handler_map.update(self.exc_handler_map)
        return clone


class NullErrorHandler:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


class Handler:
    """
    Wrapper around an exception class and the handler for it to facilitate sorting to select the most specific handler
    for a given exception.
    """

    __slots__ = ('exc_cls', 'handler')

    def __init__(self, exc_cls: Type[BaseException], handler: HandlerFunc):
        self.exc_cls = exc_cls
        self.handler = handler

    def __eq__(self, other: Handler) -> bool:
        return other.exc_cls == self.exc_cls and other.handler == self.handler

    def __lt__(self, other: Handler) -> bool:
        return issubclass(self.exc_cls, other.exc_cls)


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
