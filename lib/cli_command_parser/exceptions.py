"""
Exceptions for Command Parser

:author: Doug Skrypa
"""
# pylint: disable=W0231

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Optional, Collection, Mapping

from .utils import _parse_tree_target_repr

if TYPE_CHECKING:
    from .parameters import Parameter, BaseOption
    from .typing import ParamOrGroup
    from .parse_tree import PosNode, Word, Target

__all__ = [
    'CommandParserException',
    'ParserExit',
    'CommandDefinitionError',
    'ParameterDefinitionError',
    'AmbiguousShortForm',
    'AmbiguousParseTree',
    'UsageError',
    'ParamUsageError',
    'MultiParamUsageError',
    'AmbiguousCombo',
    'ParamConflict',
    'ParamsMissing',
    'BadArgument',
    'InvalidChoice',
    'MissingArgument',
    'TooManyArguments',
    'NoSuchOption',
    'NoActiveContext',
]


class CommandParserException(Exception):
    """Base class for all other Command Parser exceptions"""

    code: int = 3

    def show(self) -> bool:
        if message := str(self):
            print(message, file=sys.stderr)
        return True

    def exit(self):
        self.show()
        sys.exit(self.code)


class ParserExit(CommandParserException):
    """Exception used to exit with the given message and status code"""

    def __init__(self, message: str = None, code: int = 0):
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return self.message or ''


# region Developer Errors


class CommandDefinitionError(CommandParserException):
    """An error caused by providing invalid options for a Command, or an invalid combination of Parameters"""


class ParameterDefinitionError(CommandParserException):
    """An error caused by providing invalid options for a Parameter"""


class AmbiguousShortForm(ParameterDefinitionError):
    """
    Raised when a Parameter's short form contains multiple characters that would result in potentially ambiguous
    combinations with other Parameters' short forms.

    This will only be raised if ``config.ambiguous_short_combos`` is set to ``AmbiguousComboMode.STRICT``
    """

    def __init__(self, param_conflicts_map: Mapping[BaseOption, Collection[BaseOption]]):
        self.param_conflicts_map = param_conflicts_map

    def __str__(self) -> str:
        lines = []
        for param, conflicts in self.param_conflicts_map.items():
            param_str = param.format_usage(full=True, delim=' / ')
            conflicts_str = ', '.join(p.format_usage(full=True, delim=' / ') for p in conflicts)
            lines.append(f'Ambiguous short form for {param_str} - it conflicts with: {conflicts_str}')

        lines.sort()
        return '\n'.join(lines)


class AmbiguousParseTree(CommandDefinitionError):
    """Raised when a combination of parameters would result in ambiguous paths to take when parsing arguments"""

    def __init__(self, node: PosNode, target: Target, word: Word = None):
        self.node = node
        self.target = target
        self.word = word

    def __str__(self) -> str:
        node, word = self.node, self.word
        nt, st = _parse_tree_target_repr(node.target), _parse_tree_target_repr(self.target)
        if not word or word == node.word:
            return f'Conflicting targets for parse path={node.path_repr()}: {nt}, {st}'
        return f'Conflicting choices after parse path={node.parent.path_repr()}: {node.word}=>{nt}, {word}=>{st}'


# endregion

# region User Errors


class UsageError(CommandParserException):
    """Base exception for user errors"""

    message: str = None


class ParamUsageError(UsageError):
    """Error raised when a Parameter was not used correctly"""

    def __init__(self, param: Optional[ParamOrGroup], message: str = None):
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


class MultiParamUsageError(UsageError):
    """Error raised when a combination of Parameters was not used correctly"""

    def __init__(self, params: Collection[ParamOrGroup], message: str = None):
        self.params = params
        self.usage_str = ', '.join(sorted(param.format_usage(full=True, delim=' / ') for param in params))
        if message:
            self.message = message

    def _usage_msg(self) -> str:
        if self.message:
            return f'{self.usage_str} ({self.message})'
        return self.usage_str

    def __str__(self) -> str:
        return f'usage error for the following combination of arguments: {self._usage_msg()}'


class AmbiguousCombo(MultiParamUsageError):
    """Error raised when an ambiguous combination of short options were provided"""

    def __init__(self, params: Collection[ParamOrGroup], combo: str, message: str = None):
        super().__init__(params, message)
        self.combo = combo

    def __str__(self) -> str:
        return (
            f'ambiguous option combo - part of argument={self.combo!r}'
            f' may match multiple parameters: {self._usage_msg()}'
        )


class ParamConflict(MultiParamUsageError):
    """Error raised when mutually exclusive Parameters were combined"""

    def __str__(self) -> str:
        return f'argument conflict - the following arguments cannot be combined: {self._usage_msg()}'


class ParamsMissing(UsageError):
    """Error raised when one or more required Parameters were not provided"""

    def __init__(self, params: Collection[ParamOrGroup], message: str = None, partial: bool = False):
        self.params = params
        self.usage_str = ', '.join(param.format_usage(full=True, delim=' / ') for param in params)
        self.partial = partial
        if message:
            self.message = message

    def __str__(self) -> str:
        message = f' ({self.message})' if self.message else ''
        if not message:
            message = '; '.join(p.missing_hint for p in self.params if p.missing_hint)

        if len(self.params) > 1:
            mid = '- at least one of' if self.partial else '-'
            prefix = f'arguments missing {mid} the following arguments are required'
        else:
            prefix = 'argument missing - the following argument is required'
        return f'{prefix}: {self.usage_str}{message}'


class BadArgument(ParamUsageError):
    """Error raised when an invalid value is provided for a Parameter"""


class InvalidChoice(BadArgument):
    """Error raised when a value that does not match one of the pre-defined choices was provided for a Parameter"""

    def __init__(self, param: Optional[Parameter], invalid: Any, choices: Collection[Any]):
        if isinstance(invalid, Collection) and not isinstance(invalid, str):
            bad_str = f'choices: {", ".join(map(repr, invalid))}'
        else:
            bad_str = f'choice: {invalid!r}'
        choices_str = ', '.join(map(repr, choices))
        super().__init__(param, f'invalid {bad_str} (choose from: {choices_str})')


class MissingArgument(BadArgument):
    """Error raised when a value for a Parameter was not provided"""

    message = 'missing required argument value'


class TooManyArguments(BadArgument):
    """Error raised when too many values were provided for a Parameter"""

    def __init__(self, param: ParamOrGroup, message: str = None):
        msg = f'expected {param.nargs} args - cannot accept any additional args'
        super().__init__(param, f'{msg} - {message}' if message else msg)


class NoSuchOption(UsageError):
    """Error raised when an option that was not defined as a Parameter was provided"""


class NoActiveContext(CommandParserException, RuntimeError):
    """Raised when attempting to perform an action that requires an active context while no context is active."""


# endregion

# region Internal Exceptions


class Backtrack(CommandParserException):
    """Raised when backtracking took place.  Only used internally."""


class NextCommand(CommandParserException):
    """Raised by the parser to advance to the next Command in certain cases.  Only used internally."""


# endregion
