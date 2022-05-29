"""
Utilities for formatting data using RST markup

:author: Doug Skrypa
"""

from typing import Union, Dict

__all__ = ['rst_bar', 'rst_table']


BAR_CHAR_ORDER = ('#', '*', '=', '-', '^', '"')  # parts, chapters, sections, subsections, sub-subsections, paragraphs


def rst_bar(text: Union[str, int], level: int = 1) -> str:
    bar_len = text if isinstance(text, int) else len(text)
    c = BAR_CHAR_ORDER[level]
    return c * bar_len


def rst_header(text: str, level: int = 1, overline: bool = False) -> str:
    bar = rst_bar(text, level)
    return f'{bar}\n{text}\n{bar}' if overline else f'{text}\n{bar}'


TABLE_TMPL = """
.. list-table::
   :widths: {widths}

{entries}
"""


def rst_table(data: Dict[str, str], value_pad: int = 20) -> str:
    max_key = max(map(len, data))
    max_val = max(map(len, data.values()))
    widths = f'{max_key} {max_val + value_pad}'
    entries = '\n'.join(f'   * - | {key}\n     - | {value}' for key, value in data.items())
    return TABLE_TMPL.format(widths=widths, entries=entries)
