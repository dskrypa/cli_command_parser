"""
:author: Doug Skrypa
"""

from typing import TYPE_CHECKING, Type

from ..utils import ProgramMetadata, Bool
from .utils import get_usage_sub_cmds

if TYPE_CHECKING:
    from ..core import CommandType, CommandMeta
    from ..command_parameters import CommandParameters
    from ..parameters import ParamGroup, Parameter


class CommandHelpFormatter:
    def __init__(self, command: 'CommandType', params: 'CommandParameters'):
        from ..parameters import ParamGroup  # here due to circular dependency

        self.command = command
        self.params = params
        self.pos_group = ParamGroup(description='Positional arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.opt_group]

    def maybe_add_group(self, *groups: 'ParamGroup'):
        for group in groups:
            if group.group:  # prevent duplicates
                continue
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
        parts.extend(param.formatter.format_basic_usage() for param in params if param.show_in_help)
        return delim.join(parts)

    def format_help(self, width: int = 30, group_type: Bool = True, extended_epilog: Bool = True) -> str:
        meta: ProgramMetadata = self.command.__class__.meta(self.command)
        parts = [self.format_usage(), '']
        if meta.description:
            parts += [meta.description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.formatter.format_help(width=width, group_type=group_type))

        epilog = meta.format_epilog(extended_epilog)
        if epilog:
            parts.append(epilog)

        return '\n'.join(parts)
