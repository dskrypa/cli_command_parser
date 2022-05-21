"""
Compatibility module - only used in Python 3.7

Contains stdlib CPython functions / classes from Python 3.8 and 3.10
"""

from collections.abc import Callable
from threading import RLock
from typing import Generic, _GenericAlias  # noqa


# region typing


def get_origin(tp):
    # Copied from 3.8
    if isinstance(tp, _GenericAlias):
        return tp.__origin__
    if tp is Generic:
        return Generic
    return None


def _get_args(tp):
    # Copied from 3.8
    if isinstance(tp, _GenericAlias):
        res = tp.__args__
        if get_origin(tp) is Callable and res[0] is not Ellipsis:
            res = (list(res[:-1]), res[-1])
        return res
    return ()


# endregion

# region functools


_NOT_FOUND = object()


class cached_property:
    # Copied from 3.10
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                f'Cannot assign the same cached_property to two different names ({self.attrname!r} and {name!r}).'
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError('Cannot use cached_property instance without calling __set_name__ on it.')
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = (
                            f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                            f"does not support item assignment for caching {self.attrname!r} property."
                        )
                        raise TypeError(msg) from None
        return val


# endregion
