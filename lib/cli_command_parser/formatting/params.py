"""
Parameter usage / help text formatters

:author: Doug Skrypa
"""

from itertools import chain
from textwrap import indent
from typing import Type, Tuple

from ..context import ctx
from ..exceptions import NoActiveContext
from ..utils import Bool
from ..parameters import ParamBase, ParamGroup, ParamOrGroup, ChoiceMap, PassThru, BasePositional, BaseOption
from .restructured_text import RstTable
from .utils import HelpEntryFormatter, _should_add_default


class ParamHelpFormatter:
    _param_cls_fmt_cls_map = {}

    def __init_subclass__(cls, param_cls: Type[ParamBase] = None):  # noqa
        if param_cls is not None:
            cls._param_cls_fmt_cls_map[param_cls] = cls

    @classmethod
    def for_param_cls(cls, param_cls: Type['ParamBase']) -> Type['ParamHelpFormatter']:
        try:
            return cls._param_cls_fmt_cls_map[param_cls]
        except KeyError:
            pass

        for p_cls, f_cls in reversed(tuple(cls._param_cls_fmt_cls_map.items())):  # tuple() only for 3.7 compatibility
            if issubclass(param_cls, p_cls):
                return f_cls

        return ParamHelpFormatter

    def __new__(cls, param: ParamOrGroup):
        if cls is ParamHelpFormatter:
            cls = cls.for_param_cls(param.__class__)
        return super().__new__(cls)

    def __init__(self, param: ParamOrGroup):
        self.param = param

    def format_metavar(self, choice_delim: str = ',') -> str:
        param = self.param
        if param.choices:
            return '{{{}}}'.format(choice_delim.join(map(str, param.choices)))
        elif param.metavar:
            return param.metavar
        try:
            use_type_metavar = ctx.use_type_metavar
        except NoActiveContext:
            use_type_metavar = False
        if use_type_metavar and param.type is not None:
            t = param.type
            try:
                name = t.__name__
            except AttributeError:
                pass
            else:
                if name != '<lambda>':
                    return name.upper()

        return param.name.upper()

    def format_basic_usage(self) -> str:
        raise NotImplementedError

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.format_metavar()

    def format_description(self, rst: Bool = False) -> str:
        param = self.param
        description = param.help or ''
        if _should_add_default(param.default, description, param.show_default):
            pad = ' ' if description else ''
            quote = '``' if rst else ''
            description += f'{pad}(default: {quote}{param.default!r}{quote})'

        return description

    def format_help(self, width: int = 30, prefix: str = '', tw_offset: int = 0) -> str:
        usage = self.format_usage(include_meta=True, full=True)
        description = self.format_description()
        entry_width = max(20, width - tw_offset)
        text = HelpEntryFormatter(usage, description, entry_width, tw_offset=tw_offset)()
        return indent(text, prefix) if prefix else text

    def rst_row(self) -> Tuple[str, str]:
        usage = self.format_usage(include_meta=True, full=True)
        return f'``{usage}``', self.format_description(rst=True)


class PositionalHelpFormatter(ParamHelpFormatter, param_cls=BasePositional):
    def format_basic_usage(self) -> str:
        return self.format_usage()

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        metavar = self.format_metavar()
        return metavar if not full or self.param.nargs == 1 else f'{metavar} [{metavar} ...]'


class OptionHelpFormatter(ParamHelpFormatter, param_cls=BaseOption):
    def format_basic_usage(self) -> str:
        usage = self.format_usage(True)
        return usage if self.param.required else f'[{usage}]'

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        param = self.param
        if include_meta:
            metavar = self.format_metavar().replace('{', '{{').replace('}', '}}')
            fmt = '{}' if param.nargs == 0 else f'{{}} [{metavar}]' if 0 in param.nargs else f'{{}} {metavar}'
            if full:
                return delim.join(fmt.format(opt) for opt in chain(param.long_opts, param.short_opts))
            else:
                return fmt.format(param.long_opts[0])
        else:
            if full:
                return delim.join(chain(param.long_opts, param.short_opts))
            else:
                return param.long_opts[0]


class ChoiceMapHelpFormatter(PositionalHelpFormatter, param_cls=ChoiceMap):
    def format_metavar(self, choice_delim: str = ',') -> str:
        param = self.param
        if param.choices:
            return '{{{}}}'.format(choice_delim.join(map(str, filter(None, param.choices))))
        else:
            return param.metavar or param.name.upper()

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.format_metavar()

    def format_help(self, width: int = 30, prefix: str = '', tw_offset: int = 0) -> str:
        param: ChoiceMap = self.param
        usage = self.format_usage()
        entry_width = max(20, width - tw_offset)
        help_entry = HelpEntryFormatter(usage, param.description, entry_width, lpad=2, tw_offset=tw_offset)()

        parts = [f'{param.title or param._default_title}:', help_entry]
        for choice in param.choices.values():
            parts.append(choice.format_help(entry_width, lpad=4))

        parts.append('')
        text = '\n'.join(parts)
        return indent(text, prefix) if prefix else text

    def rst_table(self) -> RstTable:
        param = self.param
        table = RstTable(param.title or param._default_title, param.description)
        for choice in param.choices.values():
            usage = choice.format_usage()
            table.add_row(f'``{usage}``', choice.help)
        return table


class PassThruHelpFormatter(ParamHelpFormatter, param_cls=PassThru):
    def format_basic_usage(self) -> str:
        usage = self.format_usage()
        return f'-- {usage}' if self.param.required else f'[-- {usage}]'


class GroupHelpFormatter(ParamHelpFormatter, param_cls=ParamGroup):  # noqa
    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        choices = ','.join(mem.formatter.format_usage(include_meta, full, delim) for mem in self.param.members)
        return f'{{{choices}}}'

    def format_description(self, rst: Bool = False) -> str:
        group = self.param
        if not group.description and not group._name:
            if ctx.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
                return 'Mutually {} options'.format('exclusive' if group.mutually_exclusive else 'dependent')
            else:
                return 'Optional arguments'
        else:
            description = group.description or f'{group.name} options'
            if ctx.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
                description += ' (mutually {})'.format('exclusive' if group.mutually_exclusive else 'dependent')
            return description

    def _get_spacer(self) -> str:
        group = self.param
        if group.mutually_exclusive:
            return '\u00A6 '  # BROKEN BAR
        elif group.mutually_dependent:
            return '\u2551 '  # BOX DRAWINGS DOUBLE VERTICAL
        else:
            return '\u2502 '  # BOX DRAWINGS LIGHT VERTICAL

    def format_help(self, width: int = 30, clean: Bool = True, prefix: str = '', tw_offset: int = 0) -> str:
        """
        Prepare the help text for this group.

        :param width: The width of the option/action/command column.
        :param clean: If this group only contains other groups or Action or SubCommand parameters, then omit the
          description.
        :param prefix: Prefix to add to every line (primarily intended for use with nested groups)
        :param tw_offset: Terminal width offset for text width calculations
        :return: The formatted help text.
        """
        description = self.format_description()
        parts = [f'{description}:']

        if ctx.show_group_tree:
            spacer = self._get_spacer()
            tw_offset += 2
        else:
            spacer = ''

        nested, params = 0, 0
        for member in self.param.members:
            if not member.show_in_help:
                continue

            if isinstance(member, (ChoiceMap, ParamGroup)):
                nested += 1
                parts.append(spacer)  # Add space for readability
            else:
                params += 1
            parts.append(member.formatter.format_help(width=width, prefix=spacer, tw_offset=tw_offset))

        if clean and nested and not params:
            parts = parts[2:]  # remove description and the first spacer

        if not parts[-1].endswith('\n'):  # ensure a new line separates sections, but avoid extra lines
            parts.append(spacer)

        text = '\n'.join(parts)
        return indent(text, prefix) if prefix else text

    def rst_table(self) -> RstTable:
        table = RstTable(self.format_description())
        # TODO: non-nested when config.show_group_tree is False; maybe separate options for rst vs help
        for member in self.param.members:
            if member.show_in_help:
                try:
                    sub_table: RstTable = member.formatter.rst_table()  # noqa
                except AttributeError:
                    table.add_row(*member.formatter.rst_row())
                else:
                    sub_table.show_title = False
                    table.add_row(sub_table.title, str(sub_table))

        return table
