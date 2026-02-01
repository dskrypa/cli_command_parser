"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import typing as _t
from enum import EnumMeta as _EnumMeta
from re import Pattern as _Pattern

from ..exceptions import ParameterDefinitionError as _ParamDefinitionError
from .base import InputType
from .choices import ChoiceMap, Choices, EnumChoices
from .exceptions import InputValidationError, InvalidChoiceError
from .files import File, Json, Path, Pickle, Serialized
from .numeric import Bytes, NumRange, Range
from .patterns import Glob, Regex, RegexMode
from .time import Date, DateTime, Day, DTFormatMode, Month, Time, TimeDelta
from .utils import FileWrapper, StatMode

if _t.TYPE_CHECKING:
    from ..typing import ChoicesType, InputTypeFunc, TypeFunc

# fmt: off
__all__ = [
    'StatMode', 'FileWrapper', 'Path', 'File', 'Serialized', 'Json', 'Pickle',
    'Bytes', 'Range', 'NumRange',
    'Choices', 'ChoiceMap', 'EnumChoices',
    'Regex', 'RegexMode', 'Glob',
    'Day', 'Month', 'TimeDelta', 'DateTime', 'Date', 'Time', 'DTFormatMode',
    'normalize_input_type',
]
# fmt: on

_INVALID_CHOICES_TYPES = (_Pattern, InputType)
_INVALID_TYPES_WITH_CHOICES = (Range, range, Regex, _Pattern, Glob)


def normalize_input_type(type_func: InputTypeFunc, param_choices: ChoicesType) -> TypeFunc | None:
    if choices_provided := param_choices is not None:
        if not param_choices:
            raise _ParamDefinitionError(f'Invalid choices={param_choices!r} - when specified, choices cannot be empty')
        elif isinstance(param_choices, range):
            return Range(param_choices, type_func)
        elif isinstance(param_choices, _INVALID_CHOICES_TYPES):
            raise _ParamDefinitionError(f'Invalid choices={param_choices!r} - use type={param_choices!r} instead')
        elif isinstance(type_func, _INVALID_TYPES_WITH_CHOICES):
            raise _ParamDefinitionError(f'Cannot combine type={type_func!r} with choices={param_choices!r}')

    match type_func:
        case None:
            return Choices(param_choices) if choices_provided else type_func
        case range():
            return Range(type_func)
        case _Pattern():
            return Regex(type_func)
        case _EnumMeta():
            enum_choices = EnumChoices(type_func)
            if choices_provided:
                return Choices(param_choices, enum_choices)
            return enum_choices

    return Choices(param_choices, type_func) if choices_provided else type_func
