"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

import typing as _t
from enum import Enum as _Enum

from .exceptions import InputValidationError, InvalidChoiceError
from .utils import StatMode, FileWrapper
from .base import InputType, TypeFunc
from .choices import Choices, ChoiceMap, EnumChoices
from .files import Path, File, Serialized, Json, Pickle
from .numeric import Range, NumRange
from .time import Day, Month, DateTime, Date, Time, DTFormatMode

# fmt: off
__all__ = [
    'StatMode', 'FileWrapper', 'Path', 'File', 'Serialized', 'Json', 'Pickle',
    'Range', 'NumRange',
    'Choices', 'ChoiceMap', 'EnumChoices',
    'Day', 'Month', 'DateTime', 'Date', 'Time', 'DTFormatMode',
    'normalize_input_type',
]
# fmt: on

InputTypeFunc = _t.Union[None, TypeFunc, InputType, range, _t.Type[_Enum]]


def normalize_input_type(
    type_func: InputTypeFunc, param_choices: _t.Optional[_t.Collection[_t.Any]]
) -> _t.Optional[TypeFunc]:
    param_choices_provided = param_choices is not None

    # TODO: If choices=range(0, 100) is used, for example, that should be turned into a Range type input
    # TODO: Test help text with range choices/type
    if param_choices_provided:
        if isinstance(param_choices, range):
            return Range(param_choices, type_func)
        elif isinstance(type_func, (Range, range)):
            raise ValueError(f'Cannot combine type={type_func!r} with choices={param_choices!r}')

    if type_func is None:
        return Choices(param_choices) if param_choices_provided else type_func
    elif isinstance(type_func, range):
        return Range(type_func)

    try:
        is_enum = issubclass(type_func, _Enum)
    except TypeError:
        pass
    else:
        if is_enum:
            enum_choices = EnumChoices(type_func)
            if param_choices_provided:
                return Choices(param_choices, enum_choices)
            return enum_choices

    return Choices(param_choices, type_func) if param_choices_provided else type_func
