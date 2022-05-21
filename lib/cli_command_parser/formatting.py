"""
:author: Doug Skrypa
"""

from shutil import get_terminal_size
from textwrap import TextWrapper
from typing import TYPE_CHECKING, Optional, Type

from .utils import ProgramMetadata, Bool

if TYPE_CHECKING:
    from .core import CommandType, CommandMeta
    from .command_parameters import CommandParameters
    from .parameters import ParamGroup, Parameter, SubCommand


class HelpFormatter:
    def __init__(self, command: 'CommandType', params: 'CommandParameters'):
        from .parameters import ParamGroup  # here due to circular dependency

        self.command = command
        self.params = params
        self.pos_group = ParamGroup(description='Positional arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.opt_group]

    def maybe_add_group(self, *groups: 'ParamGroup'):
        for group in groups:
            if group.contains_positional:
                self.pos_group.add(group)
            else:
                self.groups.append(group)

    def maybe_add_param(self, *params: 'Parameter'):
        for param in params:
            if not param.group:
                if param._positional:
                    self.pos_group.add(param)
                else:
                    self.opt_group.add(param)

    def format_usage(self, delim: str = ' ') -> str:
        cmd_mcls: Type['CommandMeta'] = self.command.__class__  # Using metaclass to avoid potentially overwritten attrs
        meta: ProgramMetadata = cmd_mcls.meta(self.command)
        if meta.usage:
            return meta.usage

        params = self.params.positionals + self.params.options  # noqa
        pass_thru = self.params.pass_thru
        if pass_thru is not None:
            params.append(pass_thru)

        parts = ['usage:', meta.prog, *get_usage_sub_cmds(self.command)]
        parts.extend(param.format_basic_usage() for param in params if param.show_in_help)
        return delim.join(parts)

    def format_help(
        self, width: int = 30, add_default: Bool = True, group_type: Bool = True, extended_epilog: Bool = True
    ):
        meta: ProgramMetadata = self.command.__class__.meta(self.command)
        parts = [self.format_usage(), '']
        if meta.description:
            parts += [meta.description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.format_help(width=width, add_default=add_default, group_type=group_type))

        epilog = meta.format_epilog(extended_epilog)
        if epilog:
            parts.append(epilog)

        return '\n'.join(parts)


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


class HelpEntryFormatter:
    def __init__(self, usage: str, description: Optional[str], width: int = 30, lpad: int = 2):
        self.usage = usage
        self.width = width
        self.lines = []
        self.term_width = get_terminal_size()[0]
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
