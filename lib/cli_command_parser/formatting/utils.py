"""
Utils for usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import Optional, Union, Any, Collection, Sequence, Iterator, Iterable, Tuple, List

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = len

from ..compat import WCTextWrapper
from ..config import ShowDefaults
from ..context import ctx
from ..utils import Bool, _NotSet

__all__ = ['format_help_entry', 'line_iter']

Strs = Union[str, Sequence[str]]
OptStrs = Optional[Strs]


def format_help_entry(
    usage: Strs,
    description: OptStrs,
    lpad: int = 2,
    tw_offset: int = 0,
    prefix: str = '',
    cont_indent: int = 2,
) -> str:
    config = ctx.config
    usage_width = max(config.min_usage_column_width, config.usage_column_width - tw_offset - 2)
    after_pad_width = usage_width - lpad
    term_width = ctx.terminal_width - tw_offset
    pad_prefix = prefix + ' ' * (lpad - len(prefix)) if prefix else ' ' * lpad

    usage = tuple(
        _indented(_norm_column((usage,) if isinstance(usage, str) else usage, term_width, cont_indent), cont_indent)
    )
    if not description:
        return '\n'.join(f'{pad_prefix}{line}' for line in usage)

    description_lines = [''] * _description_start_line(usage, after_pad_width)
    description_lines.extend(_norm_column(_single_line_strs(description), term_width - usage_width - 2))
    format_row = f'{pad_prefix}{{:<{after_pad_width}s}}  {{}}'.format
    return '\n'.join(format_row(*row).rstrip() for row in line_iter((usage, description_lines)))


# TODO: Generic Table where above one just has no borders?


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


def _norm_column(lines: Sequence[str], column_width: int, cont_indent: int = 0) -> Sequence[str]:
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


def _indented(lines: Iterable[str], cont_indent: int = 2) -> Iterator[str]:
    i_lines = iter(lines)
    yield next(i_lines)  # pylint: disable=R1708
    prefix = ' ' * cont_indent
    for line in i_lines:
        yield prefix + line


def _should_add_default(default: Any, help_text: Optional[str], param_show_default: Optional[Bool]) -> bool:
    if default is _NotSet:
        return False
    elif param_show_default is not None:
        return param_show_default
    sd = ctx.config.show_defaults
    if sd._value_ < 2 or (sd & ShowDefaults.MISSING and help_text and 'default:' in help_text):
        return False
    elif sd & ShowDefaults.ANY:
        return True
    elif sd & ShowDefaults.NON_EMPTY:
        return bool(default) or not (default is None or isinstance(default, Collection))
    else:
        return bool(default)


def line_iter(columns: Sequence[Strs]) -> Iterator[Tuple[str, ...]]:
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
