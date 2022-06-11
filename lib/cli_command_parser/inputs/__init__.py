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

__all__ = [
    'StatMode',
    'FileWrapper',
    'Path',
    'File',
    'Serialized',
    'Json',
    'Pickle',
    'Range',
    'NumRange',
    'Choices',
    'ChoiceMap',
    'EnumChoices',
    'normalize_input_type',
]

InputTypeFunc = _t.Union[None, TypeFunc, InputType, range, _t.Type[_Enum]]


def normalize_input_type(
    type_func: InputTypeFunc, param_choices: _t.Optional[_t.Collection[_t.Any]]
) -> _t.Optional[TypeFunc]:
    if type_func is None:
        return type_func
    elif isinstance(type_func, range):
        return Range(type_func)

    try:
        is_enum = issubclass(type_func, _Enum)
    except TypeError:
        is_enum = False

    if is_enum and param_choices is None:
        return EnumChoices(type_func)

    return type_func
