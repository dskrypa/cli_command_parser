"""
Exceptions for Command Parser

:author: Doug Skrypa
"""

import sys
from typing import TYPE_CHECKING, Any, Collection

if TYPE_CHECKING:
    from .parameters import Parameter

# TODO: Cleanup and make usage consistent
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
    'BadArgumentUsage',
    'BadOptionUsage',
    'ParserExit',
]


class CommandParserException(Exception):
    pass


class ParserExit(CommandParserException):
    def __init__(self, message: str = None, code: int = None):
        self.code = code
        self.message = message

    def __str__(self):
        return self.message or ''

    def exit(self):
        if message := self.message:
            print(message, file=sys.stderr)
        sys.exit(self.code)


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
            usage_str = param.usage_str(full=True, delim=' / ')
            return f'argument {usage_str}: {message}'


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


class BadArgumentUsage(ParamUsageError):
    pass


class BadOptionUsage(BadArgumentUsage):
    pass
