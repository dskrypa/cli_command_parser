"""
Command usage / help text formatters

:author: Doug Skrypa
"""

from __future__ import annotations

from functools import cached_property
from textwrap import TextWrapper
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Optional, Type, Union

from ..context import NoActiveContext, ctx
from ..core import get_metadata, get_params
from ..parameters.groups import ParamGroup
from ..utils import _NotSet, camel_to_snake_case
from .restructured_text import RstTable, spaced_rst_header
from .utils import PartWrapper

if TYPE_CHECKING:
    from ..command_parameters import CommandParameters
    from ..config import CommandConfig
    from ..core import CommandMeta
    from ..metadata import ProgramMetadata
    from ..parameters import BaseOption, BasePositional, Parameter, PassThru, SubCommand
    from ..typing import Bool, CommandAny, CommandCls, CommandType

__all__ = ['CommandHelpFormatter', 'get_formatter']

NameFunc = Callable[[str], str]


class CommandHelpFormatter:
    def __init__(self, command: CommandType, params: CommandParameters):
        self.command = command
        self.params = params
        self.pos_group = ParamGroup(description='Positional arguments')
        self.req_group = ParamGroup(description='Required arguments')
        self.opt_group = ParamGroup(description='Optional arguments')
        self.groups = [self.pos_group, self.req_group, self.opt_group]

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

    def maybe_add_positionals(self, params: Iterable[BasePositional]):
        self.pos_group.extend(param for param in params if not param.group)

    def maybe_add_option(self, param: Optional[Parameter]):
        if param is not None and not param.group:
            if param.required:
                self.req_group.add(param)
            else:
                self.opt_group.add(param)

    def maybe_add_options(self, params: Iterable[BaseOption]):
        for param in params:
            self.maybe_add_option(param)

    def _iter_params(self) -> Iterator[Union[BasePositional, BaseOption, PassThru]]:
        params = self.params
        yield from params.all_positionals
        # TODO: Add configurable option to reduce usage line noise, so something like [options] is displayed instead of
        #  every option+metavar, while positionals are retained?
        yield from params.options
        # TODO: Should groups be respected for the usage line?
        if params.pass_thru is not None:
            yield params.pass_thru

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
            return PartWrapper(wrap_usage_str, cont_indent, delim).join('', parts)
        return delim.join(parts)

    def format_help(self, allow_sys_argv: Bool = True) -> str:
        parts = [self.format_usage(allow_sys_argv=allow_sys_argv), '']
        if description := self._meta.description:
            parts += [description, '']

        parts.extend(group.formatter.format_help() for group in self.groups if group.show_in_help)
        if epilog := self._meta.format_epilog(ctx.config.extended_epilog, allow_sys_argv):
            parts.append(epilog)

        return '\n'.join(parts)

    # region RST Formatting

    def format_rst(
        self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1, allow_sys_argv: Bool = False
    ) -> str:
        """Generate the RST content for the Command associated with this formatter and all of its subcommands"""
        return '\n'.join(self._format_rst(fix_name, fix_name_func, init_level, allow_sys_argv))

    def _format_rst(
        self, fix_name: Bool = True, fix_name_func: NameFunc = None, init_level: int = 1, allow_sys_argv: Bool = False
    ) -> Iterator[str]:
        name = self._meta.doc_name
        if fix_name:
            name = fix_name_func(name) if fix_name_func else _fix_name(name)  # noqa

        yield from spaced_rst_header(name, init_level, False)

        config = ctx.config
        if config.show_docstring and (doc_str := self._meta.get_doc_str()):
            yield doc_str
            yield ''

        yield ''
        yield from self._cmd_rst_lines(config, allow_sys_argv=allow_sys_argv, include_epilog=True)
        if sub_command := self.params.sub_command:
            yield from self._sub_cmds_rst_lines(config, sub_command, init_level + 2, allow_sys_argv=allow_sys_argv)

    def _cmd_rst_lines(
        self,
        config: CommandConfig,
        sub_cmd_choice: str = None,
        allow_sys_argv: Bool = False,
        include_epilog: Bool = False,
    ) -> Iterator[str]:
        """Generate the RST content for the specific Command associated with this formatter"""
        yield '::'
        yield ''
        yield '    ' + self.format_usage(sub_cmd_choice=sub_cmd_choice, allow_sys_argv=allow_sys_argv, cont_indent=8)
        yield ''
        yield ''

        if description := self._meta.get_description(config.show_inherited_descriptions):
            yield description
            yield ''

        # TODO: The subcommand names in the group containing subcommand targets should link to their respective
        #  subcommand sections
        for group in self.groups:
            # TODO: Nested subcommands' local choices should not repeat the `subcommands` positional arguments section
            #  that includes the nested subcommand choice being documented
            if group.show_in_help:
                table: RstTable = group.formatter.rst_table()  # noqa
                yield from table.iter_build()

        if include_epilog and (epilog := self._meta.format_epilog(config.extended_epilog, allow_sys_argv)):
            yield epilog

    def _sub_cmds_rst_lines(
        self,
        config: CommandConfig,
        sub_command: SubCommand,
        level: int,
        choice_base: str = None,
        depth: int = 0,
        allow_sys_argv: Bool = False,
    ):
        if not sub_command.show_in_help or ((max_depth := config.sub_cmd_doc_depth) is not None and depth == max_depth):
            return
        elif depth == 0:
            yield from spaced_rst_header('Subcommands', level - 1)

        for cmd_name, choice in sub_command.choices.items():
            # TODO: There are some cases where multiple aliases for the same command (possibly local choices, possibly
            #  multiple choices all handled by a single class) would be better documented without separate sections for
            #  each choice value (should probably be configurable to explode or condense)
            choice_str = f'{choice_base} {cmd_name}' if choice_base else cmd_name
            yield from spaced_rst_header(f'Subcommand: {choice_str}', level)
            if choice.help:
                yield choice.help
                yield ''

            if (command := choice.target) is None:
                # When choice.target is None, that means it is the default choice, pointing back to the same Command
                yield from self._cmd_rst_lines(config, choice_str, allow_sys_argv)
            else:
                params = get_params(command)
                yield from params.formatter._cmd_rst_lines(config, choice_str, allow_sys_argv)
                if nested_sub_cmd := params.sub_command:
                    yield from params.formatter._sub_cmds_rst_lines(
                        config, nested_sub_cmd, level, choice_str, depth + 1, allow_sys_argv
                    )

    # endregion


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

    if parsed and parsed is not _NotSet:  # May have been called directly on the subcommand without parsing
        yield from parsed
    elif chosen := next((name for name, choice in sub_cmd_param.choices.items() if choice.target is command), None):
        yield chosen
