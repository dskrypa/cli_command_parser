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
from typing import List, Generic, _GenericAlias, _SpecialForm  # noqa

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = len

__all__ = ['get_origin', 'cached_property', 'WCTextWrapper', 'Literal']


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


try:
    from typing import Literal
except ImportError:  # Python 3.7

    class _LiteralSpecialForm(_SpecialForm, _root=True):
        def __repr__(self) -> str:
            return f'compat.{self._name}'

        def __getitem__(self, parameters):
            if not isinstance(parameters, tuple):
                parameters = (parameters,)
            return _GenericAlias(self, parameters)

    _LITERAL_DOCSTRING = """
    Special typing form to define literal types (a.k.a. value types).

    This form can be used to indicate to type checkers that the corresponding
    variable or function parameter has a value equivalent to the provided
    literal (or one of several literals):

      def validate_simple(data: Any) -> Literal[True]:  # always returns True
          ...

      MODE = Literal['r', 'rb', 'w', 'wb']
      def open_helper(file: str, mode: MODE) -> str:
          ...

      open_helper('/some/path', 'r')  # Passes type check
      open_helper('/other/path', 'typo')  # Error in type checker

    Literal[...] cannot be subclassed. At runtime, an arbitrary value
    is allowed as type argument to Literal[...], but type checkers may
    impose restrictions.
    """
    Literal = _LiteralSpecialForm('Literal', doc=_LITERAL_DOCSTRING)


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
