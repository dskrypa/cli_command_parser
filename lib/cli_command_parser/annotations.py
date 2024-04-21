"""
Utilities for extracting types from annotations.

:author: Doug Skrypa
"""

from collections.abc import Collection, Iterable
from functools import lru_cache
from inspect import isclass
from typing import Union, Optional, get_type_hints as _get_type_hints, get_origin, get_args as _get_args

try:
    from types import NoneType
except ImportError:  # Added in 3.10
    NoneType = type(None)

__all__ = ['get_descriptor_value_type']

get_type_hints = lru_cache()(_get_type_hints)  # Cache the attr:annotation mapping for each Command class


def get_descriptor_value_type(command_cls: type, attr: str) -> Optional[type]:
    try:
        annotation = get_type_hints(command_cls)[attr]
    except (KeyError, NameError):  # KeyError due to attr missing; NameError for forward references
        return None
    # Note: `inspect.get_annotations(obj)` returns a dict of where values are the string representations of the
    # discovered annotations; values in the dict returned by `typing.get_type_hints` are the actual classes / typing
    # aliases that were used, which are significantly more useful for this analysis.
    return get_annotation_value_type(annotation)


def get_annotation_value_type(annotation, from_union: bool = True, from_collection: bool = True) -> Optional[type]:
    origin = get_origin(annotation)
    # Note: get_origin returns `list` for `List[str]`, `List`, and `list[str]`; it returns `None` for `list`
    if origin is None and isinstance(annotation, type):
        return annotation
    elif from_collection and isclass(origin) and issubclass(origin, (Collection, Iterable)):
        return _type_from_collection(origin, annotation)
    elif from_union and origin is Union:
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
        return get_annotation_value_type(args[0] if args[1] is NoneType else args[1], from_union=False)
    return None


def _type_from_collection(origin, annotation) -> Optional[type]:
    if not (args := get_args(annotation)):
        return origin  # The annotation was a collection with no content types specified
    n_args = len(args)
    if n_args == 1 or (origin is tuple and ((n_args == 2 and args[1] is Ellipsis) or len(set(args)) == 1)):
        return get_annotation_value_type(args[0], from_collection=False)
    return None
