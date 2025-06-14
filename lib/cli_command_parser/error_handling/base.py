"""
Platform-agnostic error handling framework / handlers.
"""

from __future__ import annotations

import sys
from collections import ChainMap
from typing import Callable, Iterator, Type, TypeVar, Union

from ..exceptions import CommandParserException

__all__ = ['ErrorHandler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

E = TypeVar('E', bound=BaseException)
HandlerFunc = Callable[[E], Union[bool, int, None]]


class ErrorHandler:
    __slots__ = ('exc_handler_map',)
    _exc_handler_map: dict[Type[BaseException], Handler] = {}
    exc_handler_map: dict[Type[BaseException], Handler]

    def __init__(self):
        self.exc_handler_map = {}

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[handlers={len(self.exc_handler_map)}]>'

    def register(self, handler: HandlerFunc, *exceptions: Type[E]):
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
    def cls_handler(cls, *exceptions: Type[E]):
        def _cls_handler(handler: Union[HandlerFunc, staticmethod]):
            for exc in exceptions:
                cls._exc_handler_map[exc] = Handler(exc, handler)
            return handler

        return _cls_handler

    def iter_handlers(self, exc_type: Type[BaseException], exc: BaseException) -> Iterator[HandlerFunc]:
        exc_handler_map = ChainMap(self.exc_handler_map, self._exc_handler_map)
        try:
            yield exc_handler_map[exc_type].handler
        except KeyError:
            pass
        candidates = sorted(
            handler for ec, handler in exc_handler_map.items() if ec is not exc_type and isinstance(exc, ec)
        )
        for candidate in candidates:
            yield candidate.handler

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb) -> bool:
        if exc_type is None:
            return False

        for handler in self.iter_handlers(exc_type, exc_val):
            result = handler(exc_val)
            if result is True:
                # This explicitly checks for True since 1 == True, but 1 is treated as an intended exit code
                return True
            if result or (isinstance(result, int) and result is not False):
                sys.exit(result)

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


# By default, all error handlers should call :meth:`CommandParserException.exit` for CommandParserExceptions
ErrorHandler.cls_handler(CommandParserException)(CommandParserException.exit)  # noqa

#: Default base :class:`ErrorHandler`
error_handler: ErrorHandler = ErrorHandler()


@error_handler(BrokenPipeError)
def _handle_broken_pipe(exc: BrokenPipeError):
    # This can't be registered as a lambda function because it would break the ability to pickle the handler
    return True


#: An :class:`ErrorHandler` that does not call :func:`python:sys.exit` for
#: :class:`CommandParserExceptions<.CommandParserException>`
no_exit_handler: ErrorHandler = error_handler.copy()
no_exit_handler.register(CommandParserException.show, CommandParserException)  # noqa

#: The default :class:`ErrorHandler` (extends :obj:`error_handler`)
extended_error_handler: ErrorHandler = error_handler.copy()
