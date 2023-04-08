"""
Exceptions for custom input types / validators.

:author: Doug Skrypa
"""

from typing import Collection, Any

from ..exceptions import CommandParserException

__all__ = ['InputValidationError', 'InvalidChoiceError']


class InputValidationError(CommandParserException, ValueError):
    """Raised when a custom InputType's conversion/validation fails"""


class InvalidChoiceError(InputValidationError):
    """Error raised when a value that does not match one of the pre-defined choices was provided"""

    def __init__(self, invalid: Any, choices: Collection[Any], type_str: str = 'choice'):  # pylint: disable=W0231
        self.invalid = invalid
        self.choices = choices
        self.type_str = type_str

    def __str__(self) -> str:
        if isinstance(self.invalid, Collection) and not isinstance(self.invalid, str):
            bad_str = f'{self.type_str}s: {", ".join(map(repr, self.invalid))}'
        else:
            bad_str = f'{self.type_str}: {self.invalid!r}'

        choices_str = ', '.join(map(repr, self.choices))
        return f'invalid {bad_str} (choose from: {choices_str})'
