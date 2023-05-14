"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import typing as _t
from enum import Enum as _Enum

from ..exceptions import ParameterDefinitionError as _ParameterDefinitionError
from .exceptions import InputValidationError, InvalidChoiceError
from .utils import StatMode, FileWrapper
from .base import InputType
from .choices import Choices, ChoiceMap, EnumChoices
from .files import Path, File, Serialized, Json, Pickle
from .numeric import Range, NumRange
from .patterns import Regex, RegexMode, Glob
from .time import Day, Month, TimeDelta, DateTime, Date, Time, DTFormatMode

if _t.TYPE_CHECKING:
    from ..typing import TypeFunc, InputTypeFunc, ChoicesType

# fmt: off
__all__ = [
    'StatMode', 'FileWrapper', 'Path', 'File', 'Serialized', 'Json', 'Pickle',
    'Range', 'NumRange',
    'Choices', 'ChoiceMap', 'EnumChoices',
    'Regex', 'RegexMode', 'Glob',
    'Day', 'Month', 'TimeDelta', 'DateTime', 'Date', 'Time', 'DTFormatMode',
    'normalize_input_type',
]
# fmt: on

_INVALID_CHOICES_TYPES = (_t.Pattern, InputType)
_INVALID_TYPES_WITH_CHOICES = (Range, range, Regex, _t.Pattern, Glob)


def normalize_input_type(type_func: InputTypeFunc, param_choices: ChoicesType) -> _t.Optional[TypeFunc]:
    if choices_provided := param_choices is not None:
        if not param_choices:
            raise _ParameterDefinitionError(
                f'Invalid choices={param_choices!r} - when specified, choices cannot be empty'
            )
        elif isinstance(param_choices, range):
            return Range(param_choices, type_func)
        elif isinstance(param_choices, _INVALID_CHOICES_TYPES):
            raise _ParameterDefinitionError(f'Invalid choices={param_choices!r} - use type={param_choices!r} instead')
        elif isinstance(type_func, _INVALID_TYPES_WITH_CHOICES):
            raise _ParameterDefinitionError(f'Cannot combine type={type_func!r} with choices={param_choices!r}')

    if type_func is None:
        return Choices(param_choices) if choices_provided else type_func
    elif isinstance(type_func, range):
        return Range(type_func)
    elif isinstance(type_func, _t.Pattern):
        return Regex(type_func)

    try:
        is_enum = issubclass(type_func, _Enum)
    except TypeError:
        pass
    else:
        if is_enum:
            enum_choices = EnumChoices(type_func)
            if choices_provided:
                return Choices(param_choices, enum_choices)
            return enum_choices

    return Choices(param_choices, type_func) if choices_provided else type_func
