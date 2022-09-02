"""
Command usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type, Callable, Iterator, Iterable, Optional, Union

from ..context import ctx, NoActiveContext
from ..parameters.groups import ParamGroup
from ..utils import camel_to_snake_case
from .restructured_text import rst_header, RstTable

if TYPE_CHECKING:
    from ..core import CommandType, CommandMeta
    from ..command_parameters import CommandParameters
    from ..commands import Command
    from ..metadata import ProgramMetadata
    from ..parameters import Parameter, BasePositional, BaseOption, SubCommand
    from ..typing import Bool

__all__ = ['CommandHelpFormatter', 'get_formatter']

NameFunc = Callable[[str], str]


class CommandHelpFormatter:
    def __init__(self, command: CommandType, params: CommandParameters):
        self.command = command
        self.params = params
        self.pos_group = ParamGroup(description='Positional arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.opt_group]

    def maybe_add_groups(self, groups: Iterable[ParamGroup]):
        for group in groups:
            if group.group:  # prevent duplicates
                continue
            if group.contains_positional:
                self.pos_group.add(group)
            else:
                self.groups.append(group)

    def maybe_add_option(self, param: Optional[Parameter]):
        if param is not None and not param.group:
            self.opt_group.add(param)

    def maybe_add_positionals(self, params: Iterable[BasePositional]):
        self.pos_group.extend(param for param in params if not param.group)

    def maybe_add_options(self, params: Iterable[BaseOption]):
        self.opt_group.extend(param for param in params if not param.group)

    def _get_meta(self) -> ProgramMetadata:
        cmd_mcls: Type[CommandMeta] = self.command.__class__  # Using metaclass to avoid potentially overwritten attrs
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

    def format_help(self) -> str:
        meta = self._get_meta()
        parts = [self.format_usage(), '']
        if meta.description:
            parts += [meta.description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.formatter.format_help())

        epilog = meta.format_epilog(ctx.config.extended_epilog)
        if epilog:
            parts.append(epilog)

        return '\n'.join(parts)

    def _format_rst(self, include_epilog: Bool = False, sub_cmd_choice: str = None) -> Iterator[str]:
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
            epilog = meta.format_epilog(ctx.config.extended_epilog)
            if epilog:
                yield epilog

    def format_rst(self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1) -> str:
        """Generate the RST content for the Command associated with this formatter and all of its subcommands"""
        meta = self._get_meta()
        name = meta.doc_name
        if fix_name:
            name = fix_name_func(name) if fix_name_func else _fix_name(name)

        parts = [rst_header(name, init_level), '']
        if ctx.config.show_docstring:
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
                parts.extend(get_formatter(choice.target)._format_rst(sub_cmd_choice=cmd_name))

        return '\n'.join(parts)


def _fix_name(name: str) -> str:
    return camel_to_snake_case(name).replace('_', ' ').title()


def _get_params(command: CommandType) -> CommandParameters:
    cmd_mcls: Type[CommandMeta] = command.__class__  # Using metaclass to avoid potentially overwritten attrs
    if not issubclass(cmd_mcls, type):
        command, cmd_mcls = cmd_mcls, cmd_mcls.__class__
    return cmd_mcls.params(command)


def get_formatter(command: Union[CommandType, Command]) -> CommandHelpFormatter:
    """Get the :class:`CommandHelpFormatter` for the given Command"""
    return _get_params(command).formatter


def get_usage_sub_cmds(command: CommandType):
    cmd_mcs: Type[CommandMeta] = command.__class__  # Using metaclass to avoid potentially overwritten attrs
    parent: CommandType = cmd_mcs.parent(command)
    if not parent:
        return []

    cmd_chain = get_usage_sub_cmds(parent)

    sub_cmd_param: SubCommand = cmd_mcs.params(parent).sub_command
    if not sub_cmd_param:
        return cmd_chain

    try:
        parsed = ctx.get_parsed_value(sub_cmd_param)
    except NoActiveContext:
        parsed = []

    if parsed:  # May have been called directly on the subcommand without parsing
        cmd_chain.extend(parsed)
        return cmd_chain

    for name, choice in sub_cmd_param.choices.items():
        if choice.target is command:
            cmd_chain.append(name)
            break

    return cmd_chain
