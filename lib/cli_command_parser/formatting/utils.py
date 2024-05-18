"""
Utils for usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Collection, Iterator, Optional, Sequence

from ..compat import WCTextWrapper
from ..config import ShowDefaults
from ..context import ctx
from ..utils import _NotSet, wcswidth

if TYPE_CHECKING:
    from ..typing import Bool, IStrs, StrIter

__all__ = ['format_help_entry', 'line_iter']


def format_help_entry(
    usage_parts: StrIter,
    description: IStrs | None,
    prefix: str = '',
    *,
    lpad: int = 2,
    usage_cont_indent: int = 2,
    usage_delim: str = ', ',
) -> str:
    """
    :param usage_parts: Individual usage parts.  That is, for an ``Option('--foo', '-f')``, separate strings for
      ``'--foo FOO'`` and ``'-f FOO'``.
    :param description: The description (``help='...'`` value) of the Parameter that is being documented.
    :param prefix: A prefix to be included on every line (such as when ``show_group_tree=True``).
    :param lpad: Minimum indentation (number of spaces) that should be applied to each line as a prefix.  If an
      explicit ``prefix`` is provided, then the padding will be reduced based on the length of the provided prefix.
    :param usage_cont_indent: Continuation indentation to apply when the ``usage_parts`` need to span multiple lines.
    :param usage_delim: The delimiter that should be used to join the ``usage_parts``.
    :return: The formatted ``--help`` entry.
    """
    if prefix:
        line_prefix = prefix + ' ' * (lpad - len(prefix))
    else:
        line_prefix = ' ' * lpad

    config = ctx.config
    usage_width = config.usage_column_width
    term_width = ctx.terminal_width

    wrapper = PartWrapper(
        usage_width if config.strict_usage_column_width else term_width, usage_cont_indent, usage_delim
    )
    if description:
        return wrapper.format_help_entry(line_prefix, usage_parts, description, usage_width, term_width)
    else:
        return wrapper.join(line_prefix, usage_parts)


class PartWrapper:
    __slots__ = ('max_width', 'cont_indent', 'delim', '_widths')

    def __init__(self, max_width: int = 30, cont_indent: int = 0, delim: str = ', '):
        self.max_width = max_width
        self.cont_indent = cont_indent
        self.delim = delim
        self._widths = []

    def join(self, prefix: str, parts: StrIter) -> str:
        if prefix:
            return '\n'.join(prefix + line for line in self.combine_and_wrap(parts))
        else:
            return '\n'.join(self.combine_and_wrap(parts))

    def format_help_entry(
        self, prefix: str, usage: StrIter, description: IStrs, usage_width: int, term_width: int
    ) -> str:
        after_pad_width = usage_width - len(prefix) - 2  # Constant -2 accounts for the spaces in format_row below

        usage_lines = tuple(self.combine_and_wrap(usage))
        description_lines = self._prepare_description_lines(description, after_pad_width, term_width - usage_width)

        format_row = f'{prefix}{{:<{after_pad_width}s}}  {{}}'.format
        return '\n'.join(format_row(*row).rstrip() for row in line_iter(usage_lines, description_lines))

    def _combine_parts(self, line_parts: list[str]) -> str:
        if self._widths:
            return (' ' * self.cont_indent) + self.delim.join(line_parts)
        else:
            return self.delim.join(line_parts)

    def combine_and_wrap(self, parts: StrIter) -> Iterator[str]:
        """Combine the given strings using the given delimiter, wrapping to a new line at max_width."""
        delim_end = self.delim.rstrip()
        delim_len = len(self.delim)
        delim_end_len = len(delim_end)
        max_width = self.max_width - delim_end_len
        line_parts = []
        last = None
        chunk_len = last_len = 0

        for part in parts:
            part_len = wcswidth(part)
            last_chunk_len = chunk_len
            chunk_len += (part_len + delim_len) if line_parts else part_len
            if (max_delta := max_width - chunk_len) <= 0:
                if last:
                    self._widths.append(last_len + delim_end_len)
                    yield last + delim_end

                if line_parts and max_delta < 0:
                    # The new chunk length exceeds the max, so the part should be excluded from the current chunk
                    last_len = last_chunk_len
                    last = self._combine_parts(line_parts)
                    line_parts = [part]
                    chunk_len = self.cont_indent + part_len
                else:
                    # The new chunk length equals the max, or the chunk is empty, so the part should be included
                    line_parts.append(part)
                    last_len = chunk_len
                    last = self._combine_parts(line_parts)
                    line_parts = []
                    chunk_len = self.cont_indent
            else:
                line_parts.append(part)

        if line_parts:
            if last:
                self._widths.append(last_len + delim_end_len)
                yield last + delim_end

            yield self._combine_parts(line_parts)  # This needs to be called before adding the len to widths
            self._widths.append(chunk_len)
        elif last:
            self._widths.append(last_len)
            yield last

    def _prepare_description_lines(self, description: IStrs, after_pad_width: int, column_width: int):
        if start_line := self._get_description_start_line(after_pad_width):
            yield from [''] * start_line

        yield from _normalize_column_width(_single_line_strs(description), column_width)

    def _get_description_start_line(self, after_pad_width: int) -> int:
        if max(self._widths, default=0) <= after_pad_width:
            return 0

        line = len(self._widths)
        for width in self._widths[::-1]:
            if width > after_pad_width:
                break
            line -= 1
        return line


def _single_line_strs(lines: IStrs) -> list[str]:
    if isinstance(lines, str):
        lines = (lines,)
    return [line for full_line in lines for line in full_line.splitlines()]


def _normalize_column_width(lines: Sequence[str], column_width: int) -> Iterator[str]:
    if max(map(wcswidth, lines)) <= column_width:
        yield from lines
    else:
        tw = WCTextWrapper(column_width, break_long_words=True, break_on_hyphens=True)
        for line in lines:
            if wcswidth(line) >= column_width:
                yield from tw.wrap(line)
            else:
                yield line


def _should_add_default(default: Any, help_text: Optional[str], param_show_default: Optional[Bool]) -> bool:
    if default is _NotSet:
        return False
    elif param_show_default is not None:
        return param_show_default
    sd = ctx.config.show_defaults
    if sd._value_ < 2 or (sd & ShowDefaults.MISSING and help_text and 'default:' in help_text):  # noqa
        return False
    elif sd & ShowDefaults.ANY:
        return True
    elif sd & ShowDefaults.NON_EMPTY:
        return bool(default) or not (default is None or isinstance(default, Collection))
    else:
        return bool(default)


def line_iter(*columns: IStrs) -> Iterator[list[str, ...]]:
    """More complicated than what would be necessary for just 2 columns, but this will scale to handle 3+"""
    exhausted = 0
    column_count = len(columns)

    def _iter(column: IStrs) -> Iterator[str]:
        nonlocal exhausted
        yield from column.splitlines() if isinstance(column, str) else column
        exhausted += 1
        while True:
            yield ''

    column_iters = [_iter(c) for c in columns]
    while True:
        row = [next(ci) for ci in column_iters]  # pylint: disable=R1708
        if exhausted == column_count:  # `while exhausted < column_count:` always results in 1 extra row
            break
        yield row
