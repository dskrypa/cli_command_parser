"""
:author: Doug Skrypa
"""

import platform
import sys
from typing import Type, Callable, Union, Optional

from .exceptions import CommandParserException

__all__ = ['ErrorHandler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

WINDOWS = platform.system().lower() == 'windows'


class ErrorHandler:
    _exc_handler_map: dict[Type[BaseException], Callable] = {}

    def __init__(self):
        self.exc_handler_map: dict[Type[BaseException], Callable] = {}

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
            if handler := next((f for ec, f in exc_handler_map.items() if isinstance(exc, ec)), None):
                return handler
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb) -> bool:
        if handler := self.get_handler(exc_type, exc_val):
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

if WINDOWS or (sys.argv and sys.argv[0].lower().endswith('pytest')):

    @extended_error_handler(OSError)
    def _handle_os_error(e: OSError):
        if e.errno == 22:
            # When using |head, the pipe will be closed when head is done, but Python will still think that it
            # is open - checking whether sys.stdout is writable or closed doesn't work, so triggering the
            # error again seems to be the most reliable way to detect this (hopefully) without false positives
            try:
                sys.stdout.write('\n')
                sys.stdout.flush()
            except OSError:
                return None
            else:
                return False  # If it wasn't the expected error, let the main Exception handler handle it
        else:
            return False
