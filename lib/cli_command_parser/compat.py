"""
Compatibility / Patch module - used to back-port features to Python 3.7 and to avoid breaking changes in Enum/Flag in
3.11.

Contains stdlib CPython functions / classes from Python 3.8 and 3.10.

The :class:`WCTextWrapper` in this module extends the stdlib :class:`python:textwrap.TextWrapper` to support wide
characters.
"""

from collections.abc import Callable
from textwrap import TextWrapper
from threading import RLock
from typing import List, Generic, _GenericAlias  # noqa

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = len


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


# region textwrap


class WCTextWrapper(TextWrapper):
    """
    Patches the ``_wrap_chunks`` method to use :func:`wcwidth:wcwidth.wcswidth` instead of :func:`python:len` (when the
    optional ``wcwidth`` dependency is available).  Minimal formatting changes are applied.  No logic has been changed.
    """

    def _wrap_chunks(self, chunks: List[str]) -> List[str]:
        """
        _wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of length 'self.width' or less.  (If
        'break_long_words' is false, some lines may be longer than this.)  Chunks correspond roughly to words and the
        whitespace between them: each chunk is indivisible (modulo 'break_long_words'), but a line break can come
        between any two chunks.  Chunks should not have internal whitespace; ie. a chunk is either all whitespace or a
        "word". Whitespace chunks will be removed from the beginning and end of lines, but apart from that whitespace
        is preserved.
        """
        if self.width <= 0:
            raise ValueError(f'invalid width {self.width!r} (must be > 0)')
        if self.max_lines is not None:
            if self.max_lines > 1:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            if len(indent) + len(self.placeholder.lstrip()) > self.width:
                raise ValueError('placeholder too large for max width')

        lines = []
        # Arrange in reverse order so items can be efficiently popped from a stack of chucks.
        chunks.reverse()
        while chunks:
            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Figure out which static string will prefix this line.
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            # Maximum width for this line.
            width = self.width - len(indent)

            # First chunk on line is whitespace -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                chunk_len = wcswidth(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + chunk_len <= width:
                    cur_line.append(chunks.pop())
                    cur_len += chunk_len

                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to fit on *any* line (not just this one).
            if chunks and wcswidth(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(wcswidth, cur_line))

            # If the last chunk on this line is all whitespace, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                cur_len -= wcswidth(cur_line[-1])
                del cur_line[-1]

            if cur_line:
                if (
                    self.max_lines is None
                    or len(lines) + 1 < self.max_lines
                    or (not chunks or self.drop_whitespace and len(chunks) == 1 and not chunks[0].strip())
                    and cur_len <= width
                ):
                    # Convert current line back to a string and store it in list of all lines (return value).
                    lines.append(indent + ''.join(cur_line))
                else:
                    while cur_line:
                        if cur_line[-1].strip() and cur_len + len(self.placeholder) <= width:
                            cur_line.append(self.placeholder)
                            lines.append(indent + ''.join(cur_line))
                            break
                        cur_len -= wcswidth(cur_line[-1])
                        del cur_line[-1]
                    else:
                        if lines:
                            prev_line = lines[-1].rstrip()
                            if wcswidth(prev_line) + len(self.placeholder) <= self.width:
                                lines[-1] = prev_line + self.placeholder
                                break

                        lines.append(indent + self.placeholder.lstrip())
                    break

        return lines


# endregion
