"""
Exceptions for Command Parser

:author: Doug Skrypa
"""
# pylint: disable=W0231

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Collection

if TYPE_CHECKING:
    from .parameters import Parameter, ParamOrGroup

__all__ = [
    'CommandParserException',
    'CommandDefinitionError',
    'ParameterDefinitionError',
    'UsageError',
    'ParamUsageError',
    'BadArgument',
    'InvalidChoice',
    'MissingArgument',
    'NoSuchOption',
    'ParserExit',
    'ParamConflict',
    'ParamsMissing',
    'NoActiveContext',
]


class CommandParserException(Exception):
    """Base class for all other Command Parser exceptions"""

    code: int = 2

    def show(self):
        message = str(self)
        if message:
            print(message, file=sys.stderr)

    def exit(self):
        self.show()
        sys.exit(self.code)


class ParserExit(CommandParserException):
    """Exception used to exit with the given message and status code"""

    def __init__(self, message: str = None, code: int = None):
        self.code = code
        self.message = message

    def __str__(self):
        return self.message or ''


# region Developer Errors


class CommandDefinitionError(CommandParserException):
    """An error caused by providing invalid options for a Command, or an invalid combination of Parameters"""


class ParameterDefinitionError(CommandParserException):
    """An error caused by providing invalid options for a Parameter"""


# endregion

# region User Errors


class UsageError(CommandParserException):
    """Base exception for user errors"""


class ParamUsageError(UsageError):
    """Error raised when a Parameter was not used correctly"""

    message: str = None

    def __init__(self, param: ParamOrGroup, message: str = None):
        self.param = param
        self.usage_str = param.format_usage(full=True, delim=' / ') if param else ''
        if message:
            self.message = message

    def __str__(self) -> str:
        message = self.message or 'usage error'
        if self.param is None:
            return message
        else:
            return f'argument {self.usage_str}: {message}'


class ParamConflict(UsageError):
    """Error raised when mutually exclusive Parameters were combined"""

    message: str = None

    def __init__(self, params: Collection[ParamOrGroup], message: str = None):
        self.params = params
        self.usage_str = ', '.join(param.format_usage(full=True, delim=' / ') for param in params)
        if message:
            self.message = message

    def __str__(self) -> str:
        message = f' ({self.message})' if self.message else ''
        return f'argument conflict - the following arguments cannot be combined: {self.usage_str}{message}'


class ParamsMissing(UsageError):
    """Error raised when one or more required Parameters were not provided"""

    message: str = None

    def __init__(self, params: Collection[ParamOrGroup], message: str = None):
        self.params = params
        self.usage_str = ', '.join(param.format_usage(full=True, delim=' / ') for param in params)
        if message:
            self.message = message

    def __str__(self) -> str:
        message = f' ({self.message})' if self.message else ''
        if not message:
            message = '; '.join(p.missing_hint for p in self.params if p.missing_hint)

        if len(self.params) > 1:
            prefix = 'arguments missing - the following arguments are required'
        else:
            prefix = 'argument missing - the following argument is required'
        return f'{prefix}: {self.usage_str}{message}'


class BadArgument(ParamUsageError):
    """Error raised when an invalid value is provided for a Parameter"""


class InvalidChoice(BadArgument):
    """Error raised when a value that does not match one of the pre-defined choices was provided for a Parameter"""

    def __init__(self, param: Parameter, invalid: Any, choices: Collection[Any]):
        if isinstance(invalid, Collection) and not isinstance(invalid, str):
            bad_str = 'choices: {}'.format(', '.join(map(repr, invalid)))
        else:
            bad_str = f'choice: {invalid!r}'
        choices_str = ', '.join(map(repr, choices))
        super().__init__(param, f'invalid {bad_str} (choose from: {choices_str})')


class MissingArgument(BadArgument):
    """Error raised when a value for a Parameter was not provided"""

    message = 'missing required argument value'


class NoSuchOption(UsageError):
    """Error raised when an option that was not defined as a Parameter was provided"""


class NoActiveContext(CommandParserException, RuntimeError):
    """Raised when attempting to perform an action that requires an active context while no context is active."""


# endregion

# region Internal Exceptions


class UnsupportedAction(CommandParserException):
    """Indicates that an attempted action cannot be completed.  Only used internally."""


class Backtrack(CommandParserException):
    """Raised when backtracking took place"""


# endregion
