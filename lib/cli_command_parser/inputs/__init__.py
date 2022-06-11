"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

from typing import Callable, Optional, Union, Any

from .utils import StatMode, FileWrapper
from .base import InputType
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
    'normalize_input_type',
]

TypeFunc = Callable[[str], Any]
InputTypeFunc = Union[TypeFunc, InputType, range]


def normalize_input_type(type_func: Optional[TypeFunc]) -> Union[TypeFunc, InputType, None]:
    if type_func is None:
        return type_func
    elif isinstance(type_func, range):
        return Range(type_func)
    return type_func
