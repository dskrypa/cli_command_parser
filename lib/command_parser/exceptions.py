"""
Exceptions for Command Parser

:author: Doug Skrypa
"""

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
]


class CommandParserException(Exception):
    pass


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
