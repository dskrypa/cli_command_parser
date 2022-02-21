"""
:author: Doug Skrypa
"""

from typing import TYPE_CHECKING

from .parameters import BasePositional, BaseOption, ParamGroup, ParamOrGroup
from .utils import ProgramMetadata, Bool

if TYPE_CHECKING:
    from .commands import CommandType
    from .parser import CommandParser


class HelpFormatter:
    def __init__(self, command: 'CommandType', parser: 'CommandParser'):
        self.command = command
        self.parser = parser
        self.pos_group = ParamGroup(description='Positional arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.opt_group]

    def maybe_add(self, *params: ParamOrGroup):
        for param in params:
            if isinstance(param, ParamGroup):
                if any(isinstance(p, BasePositional) for p in param):
                    self.pos_group.add(param)
                else:
                    self.groups.append(param)
            elif not param.group:
                if isinstance(param, BasePositional):
                    self.pos_group.add(param)
                else:
                    self.opt_group.add(param)

    def format_usage(self, delim: str = ' ') -> str:
        meta: ProgramMetadata = self.command._Command__meta
        if usage := meta.usage:
            return usage
        parts = ['usage:', meta.prog]
        for param in self.parser.positionals:  # type: BasePositional
            parts.append(param.format_usage())
        for param in self.parser.options:  # type: BaseOption
            parts.append('[{}]'.format(param.format_usage(True)))
        return delim.join(parts)

    def format_help(
        self, width: int = 30, add_default: Bool = True, group_type: Bool = True, extended_epilog: Bool = True
    ):
        meta: ProgramMetadata = self.command._Command__meta
        parts = [self.format_usage(), '']
        if description := meta.description:
            parts += [description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.format_help(width=width, add_default=add_default, group_type=group_type))

        if epilog := meta.format_epilog(extended_epilog):
            parts.append(epilog)

        return '\n'.join(parts)
