"""
Utils for usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any, Collection, Sequence, Iterator, Iterable, Tuple, List

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = len

from ..compat import WCTextWrapper
from ..config import ShowDefaults
from ..context import ctx
from ..utils import _NotSet

if TYPE_CHECKING:
    from ..typing import Bool, Strs, OptStrs

__all__ = ['format_help_entry', 'line_iter']


def format_help_entry(
    usage_parts: Iterable[str],
    description: OptStrs,
    prefix: str = '',
    tw_offset: int = 0,
    *,
    lpad: int = 2,
    cont_indent: int = 2,
    usage_delim: str = ', ',
) -> str:
    if prefix:
        line_prefix = prefix + ' ' * (lpad - len(prefix))
    else:
        line_prefix = ' ' * lpad

    config = ctx.config
    term_width = ctx.terminal_width - tw_offset
    usage_width = max(config.min_usage_column_width, config.usage_column_width - tw_offset - 2)
    if not description:
        usage_line_iter = combine_and_wrap(usage_parts, term_width, cont_indent, usage_delim)
        return '\n'.join(line_prefix + line for line in usage_line_iter)

    after_pad_width = usage_width - lpad
    usage_lines = tuple(combine_and_wrap(usage_parts, term_width, cont_indent, usage_delim))
    description_lines = [''] * _description_start_line(usage_lines, after_pad_width)
    description_lines.extend(_normalize_column_width(_single_line_strs(description), term_width - usage_width - 2))
    format_row = f'{line_prefix}{{:<{after_pad_width}s}}  {{}}'.format
    return '\n'.join(format_row(*row).rstrip() for row in line_iter(usage_lines, description_lines))


def combine_and_wrap(parts: Iterable[str], max_width: int, cont_indent: int = 0, delim: str = ', ') -> Iterator[str]:
    """Combine the given strings using the given delimiter, wrapping to a new line at max_width."""
    delim_end = delim.rstrip()
    delim_len = len(delim)
    line_len = delim_end_len = len(delim_end)
    line_parts = []
    last = None
    for part in parts:
        part_len = len(part)
        line_len += part_len + delim_len
        if line_len >= max_width:
            if last:
                yield last + delim_end
                prefix = ' ' * cont_indent
            else:
                prefix = ''

            if line_parts and line_len > max_width:
                last = prefix + delim.join(line_parts)
                line_parts = [part]
                line_len = delim_end_len + cont_indent + part_len
            else:
                line_parts.append(part)
                last = prefix + delim.join(line_parts)
                line_parts = []
                line_len = delim_end_len + cont_indent - delim_len
        else:
            line_parts.append(part)

    if line_parts:
        if last:
            yield last + delim_end
            prefix = ' ' * cont_indent
        else:
            prefix = ''
        yield prefix + delim.join(line_parts)
    elif last:
        yield last


def _description_start_line(usage: Iterable[str], max_usage_width: int) -> int:
    widths = [wcswidth(line) for line in usage]
    if max(widths, default=0) <= max_usage_width:
        return 0

    widths.reverse()
    line = len(widths)
    for width in widths:
        if width > max_usage_width:
            break
        line -= 1
    return line


def _single_line_strs(lines: Strs) -> List[str]:
    if isinstance(lines, str):
        lines = (lines,)
    return [line for full_line in lines for line in full_line.splitlines()]


def _normalize_column_width(lines: Sequence[str], column_width: int, cont_indent: int = 0) -> Sequence[str]:
    max_width = max(map(wcswidth, lines)) + cont_indent
    if max_width <= column_width:
        return lines

    tw = WCTextWrapper(column_width, break_long_words=True, break_on_hyphens=True)
    fixed = []
    for line in lines:
        if wcswidth(line) + cont_indent >= column_width:
            fixed.extend(tw.wrap(line))
        else:
            fixed.append(line)

    return fixed


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


def line_iter(*columns: Strs) -> Iterator[Tuple[str, ...]]:
    """More complicated than what would be necessary for just 2 columns, but this will scale to handle 3+"""
    exhausted = 0
    column_count = len(columns)

    def _iter(column: Strs) -> Iterator[str]:
        nonlocal exhausted
        yield from column.splitlines() if isinstance(column, str) else column
        exhausted += 1
        while True:
            yield ''

    column_iters = tuple(_iter(c) for c in columns)
    while True:
        row = tuple(next(ci) for ci in column_iters)  # pylint: disable=R1708
        if exhausted == column_count:  # `while exhausted < column_count:` always results in 1 extra row
            break
        yield row
