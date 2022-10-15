"""
Utilities for extracting types from annotations.

:author: Doug Skrypa
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from inspect import isclass
from typing import Union, Optional, get_type_hints

try:
    from typing import get_origin, get_args as _get_args  # pylint: disable=C0412
except ImportError:  # Added in 3.8; the versions from 3.8 are copied here
    from .compat import get_origin, _get_args

try:
    from types import NoneType
except ImportError:  # Added in 3.10
    NoneType = type(None)

__all__ = ['get_descriptor_value_type']


def get_descriptor_value_type(command_cls: type, attr: str) -> Optional[type]:
    try:
        annotation = get_type_hints(command_cls)[attr]
    except (KeyError, NameError):  # KeyError due to attr missing; NameError for forward references
        return None

    return get_annotation_value_type(annotation)


def get_annotation_value_type(annotation) -> Optional[type]:
    origin = get_origin(annotation)
    # Note on get_origin return values:
    # get_origin(List[str]) -> list
    # get_origin(List) -> list
    # get_origin(list[str]) -> list
    # get_origin(list) -> None
    if origin is None and isinstance(annotation, type):
        return annotation
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, annotation)
    elif origin is Union:
        return _type_from_union(annotation)
    return None


def get_args(annotation) -> tuple:
    """
    Wrapper around :func:`python:typing.get_args` for 3.7~8 compatibility, to make it behave more like it does in 3.9+
    """
    if getattr(annotation, '_special', False):  # 3.7-3.8 generic collection alias with no content types
        return ()
    return _get_args(annotation)


def _type_from_union(annotation) -> Optional[type]:
    args = get_args(annotation)
    # Note: Unions of a single argument return the argument; i.e., Union[T] returns T, so the len can never be 1
    if len(args) == 2 and NoneType in args:
        arg = args[0] if args[1] is NoneType else args[1]
    else:
        return None

    origin = get_origin(arg)
    if origin is None and isinstance(arg, type):
        return arg
    elif isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, arg)
    else:
        return None


def _type_from_collection(origin, annotation) -> Optional[type]:
    args = get_args(annotation)
    try:
        annotation = args[0]
    except IndexError:  # The annotation was a collection with no content types specified
        return origin

    n_args = len(args)
    if n_args > 1 and (origin is not tuple or not ((n_args == 2 and args[1] is Ellipsis) or len(set(args)) == 1)):
        return None

    origin = get_origin(annotation)
    if origin is None and isinstance(annotation, type):
        return annotation
    elif origin is Union:
        return _type_from_union(annotation)
    else:
        return None
