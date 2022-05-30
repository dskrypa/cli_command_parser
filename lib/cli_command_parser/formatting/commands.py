"""
Command usage / help text formatters

:author: Doug Skrypa
"""

from typing import TYPE_CHECKING, Type, Callable, Iterator

from ..context import ctx
from ..utils import Bool, ProgramMetadata, camel_to_snake_case
from .restructured_text import rst_header, RstTable
from .utils import get_usage_sub_cmds

if TYPE_CHECKING:
    from ..core import CommandType, CommandMeta
    from ..command_parameters import CommandParameters
    from ..parameters import ParamGroup, Parameter

__all__ = ['CommandHelpFormatter', 'get_formatter']

NameFunc = Callable[[str], str]


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

    def _get_meta(self) -> ProgramMetadata:
        cmd_mcls: Type['CommandMeta'] = self.command.__class__  # Using metaclass to avoid potentially overwritten attrs
        return cmd_mcls.meta(self.command)

    def format_usage(self, delim: str = ' ', sub_cmd_choice: str = None) -> str:
        meta = self._get_meta()
        if meta.usage:
            return meta.usage

        params = self.params.positionals + self.params.options  # noqa
        pass_thru = self.params.pass_thru
        if pass_thru is not None:
            params.append(pass_thru)

        parts = ['usage:', meta.prog]
        if sub_cmd_choice:
            parts.append(sub_cmd_choice)
        else:
            parts.extend(get_usage_sub_cmds(self.command))

        parts.extend(param.formatter.format_basic_usage() for param in params if param.show_in_help)
        return delim.join(parts)

    def format_help(self, width: int = 30) -> str:
        meta = self._get_meta()
        parts = [self.format_usage(), '']
        if meta.description:
            parts += [meta.description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.formatter.format_help(width=width))  # noqa

        epilog = meta.format_epilog(ctx.extended_epilog)
        if epilog:
            parts.append(epilog)

        return '\n'.join(parts)

    def _format_rst(
        self, include_epilog: Bool = False, sub_cmd_choice: str = None, init_level: int = 1
    ) -> Iterator[str]:
        """Generate the RST content for the specific Command associated with this formatter"""
        meta = self._get_meta()
        yield from ('::', '', '    ' + self.format_usage(sub_cmd_choice=sub_cmd_choice), '', '')  # noqa
        if meta.description:
            yield meta.description
            yield ''

        for group in self.groups:
            if group.show_in_help:
                table: RstTable = group.formatter.rst_table()  # noqa
                yield from table.iter_build()  # noqa

        if include_epilog:
            epilog = meta.format_epilog(ctx.extended_epilog)
            if epilog:
                yield epilog

    def format_rst(self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1) -> str:
        """Generate the RST content for the Command associated with this formatter and all of its subcommands"""
        meta = self._get_meta()
        name = meta.doc_name
        if fix_name:
            name = fix_name_func(name) if fix_name_func else _fix_name(name)

        parts = [rst_header(name, init_level), '']
        if ctx.show_docstring:
            doc_str = meta.doc_str.strip() if meta.doc_str else None
            if doc_str:
                parts += [doc_str, '']

        parts.append('')
        parts.extend(self._format_rst(True))

        sub_command = _get_params(self.command).sub_command
        if sub_command and sub_command.show_in_help:
            parts += ['', rst_header('Subcommands', init_level + 1), '']
            for cmd_name, choice in sub_command.choices.items():
                parts += ['', rst_header(f'Subcommand: {cmd_name}', init_level + 2), '']
                if choice.help:
                    parts += [choice.help, '']
                parts.extend(get_formatter(choice.target)._format_rst(sub_cmd_choice=cmd_name, init_level=init_level))

        return '\n'.join(parts)


def _fix_name(name: str) -> str:
    return camel_to_snake_case(name).replace('_', ' ').title()


def _get_params(command: 'CommandType') -> 'CommandParameters':
    cmd_mcls: Type['CommandMeta'] = command.__class__  # Using metaclass to avoid potentially overwritten attrs
    if not issubclass(cmd_mcls, type):
        command, cmd_mcls = cmd_mcls, cmd_mcls.__class__
    return cmd_mcls.params(command)


def get_formatter(command: 'CommandType') -> CommandHelpFormatter:
    """Get the :class:`CommandHelpFormatter` for the given Command"""
    return _get_params(command).formatter
