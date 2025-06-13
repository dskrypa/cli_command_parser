import platform as _platform

from .base import (
    ErrorHandler,
    Handler,
    HandlerFunc,
    NullErrorHandler,
    error_handler,
    extended_error_handler,
    no_exit_handler,
)

if _platform.system().lower() == 'windows':
    from .windows import handle_kb_interrupt
else:
    from .other import handle_kb_interrupt

__all__ = ['ErrorHandler', 'Handler', 'error_handler', 'extended_error_handler', 'no_exit_handler', 'NullErrorHandler']

error_handler(KeyboardInterrupt)(handle_kb_interrupt)
