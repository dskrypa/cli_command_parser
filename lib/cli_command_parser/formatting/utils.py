"""
Utils for usage / help text formatters

:author: Doug Skrypa
"""

from shutil import get_terminal_size
from textwrap import TextWrapper
from typing import TYPE_CHECKING, Union, Optional, Any, Collection, Type, Dict

from ..config import ShowDefaults
from ..context import ctx
from ..utils import _NotSet

if TYPE_CHECKING:
    from ..core import CommandMeta, CommandType
    from ..parameters import SubCommand

__all__ = ['HelpEntryFormatter', 'get_usage_sub_cmds', 'rst_bar']


class HelpEntryFormatter:
    def __init__(self, usage: str, description: Optional[str], width: int = 30, lpad: int = 2, tw_offset: int = 0):
        self.usage = usage
        self.width = width
        self.lines = []
        self.term_width = get_terminal_size()[0] - tw_offset
        self.process_usage(usage, lpad)
        if description:
            self.process_description(description)

    def process_usage(self, usage: str, lpad: int = 2):
        if len(usage) + lpad > self.term_width:
            tw = TextWrapper(self.term_width, initial_indent=' ' * lpad, subsequent_indent=' ' * self.width)
            self.lines.extend(tw.wrap(usage))
        else:
            left_pad = ' ' * lpad
            self.lines.append(left_pad + usage)

    def process_description(self, description: str):
        full_indent = ' ' * self.width
        line = self.lines[0]
        pad_chars = self.width - len(line)
        if pad_chars < 0 or len(self.lines) != 1:
            if len(description) + self.width < self.term_width:
                self.lines.append(full_indent + description)
            else:
                tw = TextWrapper(self.term_width, initial_indent=full_indent, subsequent_indent=full_indent)
                self.lines.extend(tw.wrap(description))
        else:
            mid = ' ' * pad_chars
            line += mid + description
            if len(line) > self.term_width:
                tw = TextWrapper(self.term_width, initial_indent='', subsequent_indent=full_indent)
                self.lines = tw.wrap(line)
            else:
                self.lines = [line]

    def __call__(self):
        return '\n'.join(self.lines)


def _should_add_default(default: Any, help_text: Optional[str]) -> bool:
    if default is _NotSet:
        return False
    sd = ctx.show_defaults
    if sd.value < 2 or (sd & ShowDefaults.MISSING and help_text and 'default:' in help_text):
        return False
    elif sd & ShowDefaults.ANY:
        return True
    elif sd & ShowDefaults.NON_EMPTY:
        return bool(default) or not (default is None or isinstance(default, Collection))
    else:
        return bool(default)


def get_usage_sub_cmds(command: 'CommandType'):
    cmd_mcls: Type['CommandMeta'] = command.__class__  # Using metaclass to avoid potentially overwritten attrs
    parent: 'CommandType' = cmd_mcls.parent(command)
    if not parent:
        return []

    cmd_chain = get_usage_sub_cmds(parent)

    sub_cmd_param: 'SubCommand' = cmd_mcls.params(parent).sub_command
    if not sub_cmd_param:
        return cmd_chain

    for name, choice in sub_cmd_param.choices.items():
        if choice.target is command:
            cmd_chain.append(name)
            break

    return cmd_chain


# region RST Formatting

RST_BAR_CHAR_ORDER = ('*', '=', '-', '^')


def rst_bar(text: Union[str, int], level: int = 0) -> str:
    bar_len = text if isinstance(text, int) else len(text)
    c = RST_BAR_CHAR_ORDER[level]
    return c * bar_len


RST_TABLE_TMPL = """
.. list-table::
   :widths: {widths}

{entries}
"""
RST_TABLE_ENTRY_TMPL = '   * - | {key}\n     - | {value}'


def rst_table(data: Dict[str, str], value_pad: int = 20) -> str:
    max_key = max(map(len, data))
    max_val = max(map(len, data.values()))
    widths = f'{max_key} {max_val + value_pad}'
    entries = '\n'.join(RST_TABLE_ENTRY_TMPL.format(key=key, value=value) for key, value in data.items())
    return RST_TABLE_TMPL.format(widths=widths, entries=entries)


# endregion
