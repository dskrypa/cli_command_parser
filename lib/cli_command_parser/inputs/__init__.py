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
    from ..typing import ChoicesType, InputTypeFunc, NormalizedType, T, TypeFunc

    TypeT: _t.TypeAlias = _t.Union[_t.Type[T], TypeFunc[T], InputType[T]]

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


if _t.TYPE_CHECKING:

    @_t.overload
    def normalize_input_type(type_func: None, param_choices: None) -> None: ...

    @_t.overload
    def normalize_input_type(type_func: InputType[T], param_choices: None) -> InputType[T]: ...

    @_t.overload
    def normalize_input_type(type_func: TypeFunc[T], param_choices: None) -> TypeFunc[T]: ...

    @_t.overload
    def normalize_input_type(type_func: _t.Type[T], param_choices: None) -> _t.Type[T]: ...

    @_t.overload
    def normalize_input_type(type_func: TypeT[T] | None, param_choices: _t.Collection[T]) -> Choices[T]: ...

    @_t.overload
    def normalize_input_type(type_func: range, param_choices: _t.Any) -> Range[int]: ...

    @_t.overload
    def normalize_input_type(type_func: _Pattern, param_choices: _t.Any) -> Regex[str]: ...


def normalize_input_type(type_func: InputTypeFunc[T], param_choices: ChoicesType[T]) -> NormalizedType[T]:
    if param_choices is not None:
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
            if param_choices is None:
                return type_func
            return Choices(param_choices)
        case range():
            return Range(type_func)
        case _Pattern():
            return Regex(type_func)
        case _EnumMeta():
            enum_choices: EnumChoices = EnumChoices(type_func)
            if param_choices is None:
                return enum_choices
            return Choices(param_choices, enum_choices)

    if param_choices is None:
        return type_func
    return Choices(param_choices, type_func)
