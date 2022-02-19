"""
Exceptions for Command Parser

:author: Doug Skrypa
"""

import sys
from typing import TYPE_CHECKING, Any, Collection

if TYPE_CHECKING:
    from .parameters import Parameter

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
]


class CommandParserException(Exception):
    """Base class for all other Command Parser exceptions"""

    code: int = 2

    def show(self):
        if message := str(self):
            print(message, file=sys.stderr)

    def exit(self):
        self.show()
        sys.exit(self.code)


class ParserExit(CommandParserException):
    def __init__(self, message: str = None, code: int = None):
        self.code = code
        self.message = message

    def __str__(self):
        return self.message or ''


class CommandDefinitionError(CommandParserException):
    """An error related to the definition of a command"""


class ParameterDefinitionError(CommandParserException):
    pass


class UsageError(CommandParserException):
    pass


class ParamUsageError(UsageError):
    message: str = None

    def __init__(self, param: 'Parameter', message: str = None):
        self.param = param
        if message:
            self.message = message

    def __str__(self) -> str:
        message = self.message or 'usage error'
        if (param := self.param) is None:
            return message
        else:
            usage_str = param.format_usage(full=True, delim=' / ')
            return f'argument {usage_str}: {message}'


class ParamConflict(UsageError):
    message: str = None

    def __init__(self, params: Collection['Parameter'], message: str = None):
        self.params = params
        if message:
            self.message = message

    def __str__(self) -> str:
        params_str = ', '.join(param.format_usage(full=True, delim=' / ') for param in self.params)
        message = f' ({self.message})' if self.message else ''
        return f'argument conflict - the following arguments cannot be combined: {params_str}{message}'


class BadArgument(ParamUsageError):
    pass


class InvalidChoice(BadArgument):
    def __init__(self, param: 'Parameter', invalid: Any, choices: Collection[Any]):
        if isinstance(invalid, Collection) and not isinstance(invalid, str):
            bad_str = 'choices: {}'.format(', '.join(map(repr, invalid)))
        else:
            bad_str = f'choice: {invalid!r}'
        choices_str = ', '.join(map(repr, choices))
        super().__init__(param, f'invalid {bad_str} (choose from: {choices_str})')


class MissingArgument(BadArgument):
    message = 'missing required argument value'


class NoSuchOption(UsageError):
    pass
