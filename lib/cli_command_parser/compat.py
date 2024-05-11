"""
Compatibility / Patch module - used to back-port features to Python 3.7 and to avoid breaking changes in Enum/Flag in
3.11.

Contains stdlib CPython functions / classes from Python 3.8 and 3.10.

The :class:`WCTextWrapper` in this module extends the stdlib :class:`python:textwrap.TextWrapper` to support wide
characters.
"""

from __future__ import annotations

from textwrap import TextWrapper

from .utils import wcswidth

__all__ = ['WCTextWrapper']

# region textwrap


class WCTextWrapper(TextWrapper):
    """
    Patches the ``_wrap_chunks`` method to use :func:`wcwidth:wcwidth.wcswidth` instead of :func:`python:len` (when the
    optional ``wcwidth`` dependency is available).  Minimal formatting changes are applied.  No logic has been changed.
    """

    def _wrap_chunks(self, chunks: list[str]) -> list[str]:
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
