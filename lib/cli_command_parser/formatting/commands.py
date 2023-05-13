"""
Command usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import cached_property
from textwrap import TextWrapper
from typing import TYPE_CHECKING, Union, Type, Callable, Iterator, Iterable, Optional

from ..context import ctx, NoActiveContext
from ..core import get_params, get_metadata
from ..parameters.groups import ParamGroup
from ..utils import camel_to_snake_case
from .restructured_text import RstTable, spaced_rst_header
from .utils import combine_and_wrap

if TYPE_CHECKING:
    from ..core import CommandMeta
    from ..command_parameters import CommandParameters
    from ..metadata import ProgramMetadata
    from ..parameters import Parameter, BasePositional, BaseOption, SubCommand, PassThru
    from ..typing import Bool, CommandType, CommandCls, CommandAny

__all__ = ['CommandHelpFormatter', 'get_formatter']

NameFunc = Callable[[str], str]


class CommandHelpFormatter:
    def __init__(self, command: CommandType, params: CommandParameters):
        self.command = command
        self.params = params
        self.pos_group = ParamGroup(description='Positional arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.opt_group]

    @cached_property
    def _meta(self) -> ProgramMetadata:
        return get_metadata(self.command)

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

    def _iter_params(self) -> Iterator[Union[BasePositional, BaseOption, PassThru]]:
        params = self.params
        yield from params.all_positionals
        yield from params.options
        if (pass_thru := params.pass_thru) is not None:
            yield pass_thru

    def _usage_parts(self, sub_cmd_choice: str = None, allow_sys_argv: Bool = True) -> Iterator[str]:
        yield 'usage:'
        yield self._meta.get_prog(allow_sys_argv)
        if sub_cmd_choice:
            yield sub_cmd_choice
        else:
            yield from get_usage_sub_cmds(self.command)

        yield from (param.formatter.format_basic_usage() for param in self._iter_params() if param.show_in_help)

    def format_usage(
        self,
        delim: str = ' ',
        sub_cmd_choice: str = None,
        allow_sys_argv: Bool = True,
        cont_indent: int = 4,
    ) -> str:
        if (wrap_usage_str := ctx.config.wrap_usage_str) is True:
            wrap_usage_str = ctx.terminal_width

        if usage := self._meta.usage:
            if wrap_usage_str:
                return '\n'.join(TextWrapper(width=wrap_usage_str, subsequent_indent=' ' * cont_indent).wrap(usage))
            return usage

        parts = self._usage_parts(sub_cmd_choice, allow_sys_argv)
        if wrap_usage_str:
            return '\n'.join(combine_and_wrap(parts, wrap_usage_str, cont_indent, delim))
        return delim.join(parts)

    def format_help(self, allow_sys_argv: Bool = True) -> str:
        parts = [self.format_usage(allow_sys_argv=allow_sys_argv), '']
        if description := self._meta.description:
            parts += [description, '']

        for group in self.groups:
            if group.show_in_help:
                parts.append(group.formatter.format_help())

        if epilog := self._meta.format_epilog(ctx.config.extended_epilog, allow_sys_argv):
            parts.append(epilog)

        return '\n'.join(parts)

    def _format_rst(
        self,
        include_epilog: Bool = False,
        sub_cmd_choice: str = None,
        allow_sys_argv: Bool = False,
        show_description: Bool = True,
    ) -> Iterator[str]:
        """Generate the RST content for the specific Command associated with this formatter"""
        yield '::'
        yield ''
        yield '    ' + self.format_usage(sub_cmd_choice=sub_cmd_choice, allow_sys_argv=allow_sys_argv, cont_indent=8)
        yield ''
        yield ''

        if show_description and (description := self._meta.description):
            yield description
            yield ''

        # TODO: The subcommand names in the group containing subcommand targets should link to their respective
        #  subcommand sections
        for group in self.groups:
            if group.show_in_help:
                table: RstTable = group.formatter.rst_table()  # noqa
                yield from table.iter_build()

        if include_epilog and (epilog := self._meta.format_epilog(ctx.config.extended_epilog, allow_sys_argv)):
            yield epilog

    def _format_rst_lines(
        self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1, allow_sys_argv: Bool = False
    ) -> Iterator[str]:
        # TODO: Nested subcommands do not have full sections, but they should
        name = self._meta.doc_name
        if fix_name:
            name = fix_name_func(name) if fix_name_func else _fix_name(name)  # noqa

        yield from spaced_rst_header(name, init_level, False)

        config = ctx.config
        if config.show_docstring and (doc_str := self._meta.get_doc_str()):
            yield doc_str
            yield ''

        yield ''
        yield from self._format_rst(True, allow_sys_argv=allow_sys_argv)

        if (sub_command := get_params(self.command).sub_command) and sub_command.show_in_help:
            show_inherited_descriptions, description = config.show_inherited_descriptions, self._meta.description
            yield from spaced_rst_header('Subcommands', init_level + 1)
            for cmd_name, choice in sub_command.choices.items():
                yield from spaced_rst_header(f'Subcommand: {cmd_name}', init_level + 2)
                if choice_help := choice.help:
                    yield choice_help
                    yield ''

                try:
                    formatter = get_formatter(choice.target)
                except TypeError:  # choice.target is None (it is the default choice, pointing back to the same Command)
                    formatter = self
                    show_description = show_inherited_descriptions
                else:
                    if description and not show_inherited_descriptions:
                        show_description = formatter._meta.description != description
                    else:
                        show_description = True

                yield from formatter._format_rst(
                    sub_cmd_choice=cmd_name, allow_sys_argv=allow_sys_argv, show_description=show_description
                )

    def format_rst(
        self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1, allow_sys_argv: Bool = False
    ) -> str:
        """Generate the RST content for the Command associated with this formatter and all of its subcommands"""
        return '\n'.join(self._format_rst_lines(fix_name, fix_name_func, init_level, allow_sys_argv))


def _fix_name(name: str) -> str:
    return camel_to_snake_case(name).replace('_', ' ').title()


def get_formatter(command: CommandAny) -> CommandHelpFormatter:
    """Get the :class:`CommandHelpFormatter` for the given Command"""
    return get_params(command).formatter


def get_usage_sub_cmds(command: CommandCls):
    cmd_mcs: Type[CommandMeta] = command.__class__  # Using metaclass to avoid potentially overwritten attrs
    if not (parent := cmd_mcs.parent(command, False)):  # type: CommandType
        return

    yield from get_usage_sub_cmds(parent)

    if not (sub_cmd_param := cmd_mcs.params(parent).sub_command):  # type: SubCommand
        return

    try:
        parsed = ctx.get_parsed_value(sub_cmd_param)
    except NoActiveContext:
        parsed = []

    if parsed:  # May have been called directly on the subcommand without parsing
        yield from parsed
    elif chosen := next((name for name, choice in sub_cmd_param.choices.items() if choice.target is command), None):
        yield chosen
