"""
Utilities for formatting data using RST markup

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Iterator, Mapping, Sequence, TypeVar, Union

if TYPE_CHECKING:
    from ..typing import Bool, OptStr, Strings

__all__ = ['rst_bar', 'rst_list_table', 'RstTable']

T = TypeVar('T')
RowMaps = Sequence[Mapping[T, 'OptStr']]

# region Constants & Templates

BAR_CHAR_ORDER = ('#', '*', '=', '-', '^', '"')  # parts, chapters, sections, subsections, sub-subsections, paragraphs

LIST_TABLE_TMPL = """
.. list-table::
    :widths: {widths}

{entries}
"""
MODULE_TEMPLATE = """
{header}

.. currentmodule:: {module}

.. automodule:: {module}
   :members:
   :undoc-members:
   :show-inheritance:
""".lstrip()

# endregion


def rst_bar(text: Union[str, int], level: int = 1) -> str:
    bar_len = text if isinstance(text, int) else len(text)
    c = BAR_CHAR_ORDER[level]
    return c * bar_len


def rst_header(text: str, level: int = 1, overline: Bool = False) -> str:
    bar = rst_bar(text, level)
    return f'{bar}\n{text}\n{bar}' if overline else f'{text}\n{bar}'


def spaced_rst_header(text: str, level: int = 1, before: bool = True) -> Iterator[str]:
    if before:
        yield ''
    yield f'{text}\n{rst_bar(text, level)}'
    yield ''


def _rst_directive(
    directive: str, args: str = None, options: dict[str, Any] = None, indent: int = 4, check: Bool = False
) -> Iterator[str]:
    yield f'.. {directive}:: {args}' if args else f'.. {directive}::'
    if options:
        pre = ' ' * indent
        for key, val in options.items():
            if not check or val is not None:
                yield f'{pre}:{key}: {val}'


def rst_directive(
    directive: str, args: str = None, options: dict[str, Any] = None, indent: int = 4, check: Bool = False
) -> str:
    return '\n'.join(_rst_directive(directive, args, options, indent, check))


def _rst_toc_tree(name: str, content_fmt: str, contents: Strings, max_depth: int = 4, **kwargs) -> Iterator[str]:
    options = {'maxdepth': max_depth, **kwargs}
    yield rst_header(name, 1)
    yield ''
    yield from _rst_directive('toctree', options=options, check=True)
    yield ''
    yield from map(content_fmt.format, sorted(contents))


def rst_toc_tree(name: str, content_fmt: str, contents: Strings, max_depth: int = 4, **kwargs) -> str:
    """
    :param name: The name of the section.  Written as a header above the ``toctree`` directive.
    :param content_fmt: The format string used to indent/prefix each entry in the contents to include in this table
      of contents.
    :param contents: The names of the documents to include in this table of contents.
    :param max_depth: The maximum depth of the table of contents tree.  Use ``-1`` to allow unlimited depth.
    :param kwargs: Keyword arguments to be included as ``:key: <value>`` options to the ``toctree`` directive.
    :return: The RST header and table of contents directive as a string.
    """
    return '\n'.join(_rst_toc_tree(name, content_fmt, contents, max_depth, **kwargs))


def rst_list_table(data: dict[str, str], value_pad: int = 20) -> str:
    max_key = max(map(len, data))
    max_val = max(map(len, data.values()))
    widths = f'{max_key} {max_val + value_pad}'
    entries = '\n'.join(f'    * - | {key}\n      - | {value}' for key, value in data.items())
    return LIST_TABLE_TMPL.format(widths=widths, entries=entries)


class RstTable:
    """
    :param title: The title for this table.  Only displayed if ``show_title`` is True.
    :param subtitle: Passed as an option to the :du_directives:`table directive <table>` if ``header`` is True.
    :param headers: Columns headers to use before the first row.
    :param show_title: If True, and a title was provided, then that title will be emitted as a
      :any:`sphinx:rubric` directive by :meth:`.iter_build` before the beginning of this table.
    :param use_table_directive: If True, then the :du_directives:`table directive <table>` will be used before the
      body of this table.
    """

    __slots__ = ('title', 'subtitle', 'show_title', 'use_table_directive', '_rows', '_widths', '_updated')

    def __init__(
        self,
        title: str = None,
        subtitle: str = None,
        headers: Sequence[str] = None,
        *,
        show_title: Bool = True,
        use_table_directive: Bool = True,
    ):
        self.title = title
        self.subtitle = subtitle
        self.show_title = show_title
        self.use_table_directive = use_table_directive
        self._rows = []
        self._widths = ()
        self._updated = False
        if headers:
            self.add_row(*headers, header=True)

    @classmethod
    def from_dicts(cls, rows: RowMaps, columns: Sequence[T] = None, auto_headers: Bool = False, **kwargs) -> RstTable:
        """
        Initialize a RstTable using the given keyword arguments, and populate its rows using the given dicts and
        :meth:`.add_dict_rows`.
        """
        if not columns:
            columns = list(rows[0])
        if auto_headers:
            kwargs.setdefault('headers', columns)
        table = cls(**kwargs)
        table.add_dict_rows(rows, columns)
        return table

    @classmethod
    def from_dict(cls, data: Mapping[OptStr, OptStr], **kwargs) -> RstTable:
        """
        Initialize a RstTable using the given keyword arguments, and populate its rows using the given dict and
        :meth:`.add_kv_rows`.
        """
        table = cls(**kwargs)
        table.add_kv_rows(data)
        return table

    @property
    def widths(self) -> tuple[int, ...]:
        if self._updated:
            self._widths = tuple(max(col) for col in zip(*(row.widths() for row in self._rows)))
            self._updated = False
        return self._widths

    def add_dict_rows(self, rows: RowMaps, columns: Sequence[T] = None, add_header: Bool = False):
        """Add a row for each dict in the given sequence of rows, where the keys represent the columns."""
        if not columns:
            columns = list(rows[0])
        if add_header:
            self.add_row(*columns, header=True)

        self.add_rows((row.get(k) for k in columns) for row in rows)

    def add_kv_rows(self, data: Mapping[OptStr, OptStr]):
        """
        Add a row for each key=value pair in the given dict, where the first column contains the key and the second
        column contains the value.
        """
        self.add_rows(data.items())

    def add_rows(self, rows: Iterable[Iterable[OptStr]]):
        self._add_rows(Row([Cell(c or '') for c in columns]) for columns in rows)

    def _add_rows(self, rows: Iterable[Row]):
        self._rows.extend(rows)
        self._updated = True

    def add_row(self, *columns: OptStr, index: int = None, header: bool = False):
        """
        Add a row to the table.

        :param columns: The string values to use as columns in a single row
        :param index: If specified, insert the new row at the specified index.  By default, the new row is appended to
          the list of rows.
        :param header: If True, this row will be treated as a header row.  Does not affect insertion order.
        """
        self._add_row(Row([Cell(c or '') for c in columns], header), index)

    def _add_row(self, row: Row, index: int = None):
        if index is None:
            self._rows.append(row)
        else:
            self._rows.insert(index, row)
        self._updated = True

    def __repr__(self) -> str:
        return (
            f'<RstTable[use_table_directive={self.use_table_directive}, rows={len(self._rows)},'
            f' title={self.title!r}, widths={self.widths}]>'
        )

    def iter_build(self) -> Iterator[str]:
        if self.show_title and self.title:
            yield ''
            yield f'.. rubric:: {self.title}'
            yield ''

        if self.use_table_directive:
            yield from _rst_directive('table', options={'subtitle': self.subtitle, 'widths': 'auto'}, check=True)
            yield ''
            for line in self._iter_render():
                yield '    ' + line
        else:
            yield from self._iter_render()

        yield ''

    def _iter_render(self) -> Iterator[str]:
        col_widths = self.widths
        yield self._rows[0].render_upper_bar(col_widths)
        for row in self._rows:
            yield from row.render_lines(col_widths)

    def __str__(self) -> str:
        return '\n'.join(self.iter_build())


class Cell:
    __slots__ = ('text', 'lines', 'width', 'height', 'brd_bottom', 'brd_right')

    def __init__(self, text: str = '', *, ext_right: bool = False, ext_below: bool = False):
        self.text = text
        if text:
            self.lines = text.splitlines()
            self.width = max(map(len, self.lines))
            self.height = len(self.lines)
        else:
            self.lines = ['']
            self.width = 0
            self.height = 1

        self.brd_bottom = not ext_below
        self.brd_right = not ext_right

    def render_upper_bar(self, width: int) -> str:
        return ('-' * (width + 2)) + ('+' if self.brd_bottom else '|')

    def render_lower_bar(self, width: int, char: str = '-') -> str:
        if not self.brd_bottom:
            char = ' '
        return (char * (width + 2)) + ('+' if self.brd_bottom or self.brd_right else ' ')

    def render_lines(self, width: int, max_lines: int) -> Iterator[str]:
        format_line = f' {{:<{width}s}} {"|" if self.brd_right else " "}'.format
        for line in self.lines:
            yield format_line(line)

        for _ in range(self.height, max_lines):
            yield format_line('')

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.text!r}, width={self.width}, height={self.height}]>'


class Row:
    __slots__ = ('cells', 'header')

    def __init__(self, cells: list[Cell], header: bool = False):
        self.cells = cells
        self.header = header

    def widths(self) -> Iterator[int]:
        for cell in self.cells:
            yield cell.width

    def render_upper_bar(self, widths: Sequence[int]) -> str:
        return '+' + ''.join(cell.render_upper_bar(w) for cell, w in zip(self.cells, widths))

    def render_lower_bar(self, widths: Sequence[int]) -> str:
        char = '=' if self.header else '-'
        first = '+' if self.cells[0].brd_bottom else '|'
        return first + ''.join(cell.render_lower_bar(w, char) for cell, w in zip(self.cells, widths))

    def render_lines(self, widths: Sequence[int]) -> Iterator[str]:
        max_lines = max(cell.height for cell in self.cells)
        renderers = [cell.render_lines(w, max_lines) for cell, w in zip(self.cells, widths)]
        for cell_strs in zip(*renderers):
            yield '|' + ''.join(cell_strs)

        yield self.render_lower_bar(widths)
