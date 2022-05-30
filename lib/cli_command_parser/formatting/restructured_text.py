"""
Utilities for formatting data using RST markup

:author: Doug Skrypa
"""

from itertools import starmap
from typing import Union, Sequence, Iterator, Iterable, Any, Dict, Tuple, List

__all__ = ['rst_bar', 'rst_list_table', 'RstTable']


BAR_CHAR_ORDER = ('#', '*', '=', '-', '^', '"')  # parts, chapters, sections, subsections, sub-subsections, paragraphs


def rst_bar(text: Union[str, int], level: int = 1) -> str:
    bar_len = text if isinstance(text, int) else len(text)
    c = BAR_CHAR_ORDER[level]
    return c * bar_len


def rst_header(text: str, level: int = 1, overline: bool = False) -> str:
    bar = rst_bar(text, level)
    return f'{bar}\n{text}\n{bar}' if overline else f'{text}\n{bar}'


def _rst_directive(
    directive: str, args: str = None, options: Dict[str, Any] = None, indent: int = 4, check: bool = False
) -> Iterator[str]:
    yield f'.. {directive}:: {args}' if args else f'.. {directive}::'
    if options:
        pre = ' ' * indent
        for key, val in options.items():
            if not check or val is not None:
                yield f'{pre}:{key}: {val}'


def rst_directive(
    directive: str, args: str = None, options: Dict[str, Any] = None, indent: int = 4, check: bool = False
) -> str:
    return '\n'.join(_rst_directive(directive, args, options, indent, check))


TABLE_TMPL = """
.. list-table::
    :widths: {widths}

{entries}
"""


def rst_list_table(data: Dict[str, str], value_pad: int = 20) -> str:
    max_key = max(map(len, data))
    max_val = max(map(len, data.values()))
    widths = f'{max_key} {max_val + value_pad}'
    entries = '\n'.join(f'    * - | {key}\n      - | {value}' for key, value in data.items())
    return TABLE_TMPL.format(widths=widths, entries=entries)


class RstTable:
    def __init__(self, title: str = None, subtitle: str = None, show_title: bool = True, header: bool = True):
        self.header = header
        self.title = title
        self.subtitle = subtitle
        self.show_title = show_title
        self.rows = []
        self.widths = []

    def add_row(self, *columns: str, index: int = None):
        any_new_line, widths = _widths(columns)
        if self.widths:
            self.widths = tuple(starmap(max, zip(self.widths, widths)))
        else:
            self.widths = tuple(widths)

        columns = tuple(c or '' for c in columns)
        if index is None:
            self.rows.append((any_new_line, columns))
        else:
            self.rows.insert(index, (any_new_line, columns))

    def bar(self) -> str:
        pre = '    ' if self.header else ''
        return '+'.join([pre, *('-' * (w + 2) for w in self.widths), ''])

    def _get_row_format(self) -> str:
        pre = '    ' if self.header else ''
        return '|'.join([pre, *(f' {{:<{w}s}} ' for w in self.widths), ''])

    def __repr__(self) -> str:
        return f'<RstTable[header={self.header}, rows={len(self.rows)}, title={self.title!r}, widths={self.widths}]>'

    def iter_build(self) -> Iterator[str]:
        if self.show_title and self.title:
            yield ''
            yield f'.. rubric:: {self.title}'
            yield ''

        if self.header:
            # total_width = max(sum(self.widths), len(self.widths))
            # width_pcts = (int(round((w or 1) / total_width * 100, 0)) for w in self.widths)
            options = {
                'subtitle': self.subtitle,
                # 'width': '90%',
                'widths': 'auto',
                # 'widths': ' '.join(map(str, width_pcts)),
            }
            yield from _rst_directive('table', options=options, check=True)
            yield ''

        bar = self.bar()
        format_row = self._get_row_format().format
        for i, (any_new_line, row) in enumerate(self.rows):
            yield bar
            if any_new_line:
                for line in line_iter(row):
                    yield format_row(*line)
            else:
                yield format_row(*row)

        yield bar
        yield ''

    def __str__(self) -> str:
        return '\n'.join(self.iter_build())


def _widths(columns: Iterable[str]) -> Tuple[bool, List[int]]:
    widths = []
    any_new_line = False
    for column in columns:
        if not column:
            widths.append(0)
        elif '\n' in column:
            any_new_line = True
            widths.append(max(map(len, column.splitlines())))
        else:
            widths.append(len(column))

    return any_new_line, widths


def line_iter(columns: Sequence[str]) -> Iterator[Tuple[str, ...]]:
    """More complicated than what would be necessary for just 2 columns, but this will scale to handle 3+"""
    exhausted = 0
    column_count = len(columns)

    def _iter(column: str) -> Iterator[str]:
        nonlocal exhausted
        for line in column.splitlines():
            yield line

        exhausted += 1
        while True:
            yield ''

    column_iters = tuple(_iter(c) for c in columns)
    while True:
        row = tuple(next(ci) for ci in column_iters)
        if exhausted == column_count:  # `while exhausted < column_count:` always results in 1 extra row
            break
        yield row
