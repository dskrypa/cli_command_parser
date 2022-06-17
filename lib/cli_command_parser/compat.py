"""
Compatibility module - used to back-port features to Python 3.7 and to avoid breaking changes in Enum/Flag in 3.11

Contains stdlib CPython functions / classes from Python 3.8 and 3.10
"""

from collections.abc import Callable
from threading import RLock
from typing import Generic, _GenericAlias  # noqa


# region typing


def get_origin(tp):  # pylint: disable=C0103
    # Copied from 3.8
    if isinstance(tp, _GenericAlias):
        return tp.__origin__
    if tp is Generic:
        return Generic
    return None


def _get_args(tp):  # pylint: disable=C0103
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


class cached_property:  # pylint: disable=C0103,R0903
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
                f'instance to cache {self.attrname!r} property.'
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
                            f'does not support item assignment for caching {self.attrname!r} property.'
                        )
                        raise TypeError(msg) from None
        return val


# endregion

# region Enum / Flag


def missing_flag(cls, value):
    """Based on Flag._missing_ from 3.10 and below, which was changed drastically in 3.11"""
    original_value = value
    if value < 0:
        value = ~value
    possible_member = create_pseudo_member(cls, value)
    if original_value < 0:
        possible_member = ~possible_member
    return possible_member


def decompose_flag(flag_cls, value: int, name: str = None):
    """Based on enum._decompose from 3.10 and below, which was removed in 3.11"""
    member_map = flag_cls._member_map_
    if name is not None:
        try:
            return [member_map[name]], 0
        except KeyError:
            pass

    not_covered = value
    negative = value < 0
    members = []
    for member in member_map.values():
        member_value = member._value_
        if member_value and member_value & value == member_value:
            members.append(member)
            not_covered &= ~member_value

    if not negative:
        tmp = not_covered
        while tmp:
            flag_value = 2 ** (tmp.bit_length() - 1)  # 2 ** _high_bit(tmp)
            try:
                members.append(flag_cls._value2member_map_[flag_value])
            except KeyError:
                pass
            else:
                not_covered &= ~flag_value

            tmp &= ~flag_value

    if not members:
        try:
            members.append(flag_cls._value2member_map_[value])
        except KeyError:
            pass

    members.sort(key=lambda m: m._value_, reverse=True)
    if len(members) > 1 and members[0]._value_ == value:
        # we have the breakdown, don't need the value member itself
        members.pop(0)
    members.sort()
    return members, not_covered


def create_pseudo_member(flag_cls, value: int):
    """
    Create a composite member iff value contains only members.

    Based on enum.Flag._create_pseudo_member_ from 3.10 and below, which was removed in 3.11
    """
    try:
        return flag_cls._value2member_map_[value]  # noqa
    except KeyError:
        pass

    # verify all bits are accounted for
    _, extra_flags = decompose_flag(flag_cls, value)
    if extra_flags:
        raise ValueError(f'{value!r} is not a valid {flag_cls.__qualname__}')
    # construct a singleton enum pseudo-member
    if issubclass(flag_cls, int):
        pseudo_member = int.__new__(flag_cls)
    else:
        pseudo_member = object.__new__(flag_cls)
    pseudo_member._name_ = None
    pseudo_member._value_ = value
    # use setdefault in case another thread already created a composite with this value
    return flag_cls._value2member_map_.setdefault(value, pseudo_member)  # noqa


# endregion
