"""
Parameter usage / help text formatters

:author: Doug Skrypa
"""
# pylint: disable=W0613

from __future__ import annotations

from typing import TYPE_CHECKING, Union, Type, Callable, Tuple, Dict

from ..context import ctx
from ..parameters.base import BasePositional, BaseOption
from ..parameters.choice_map import ChoiceMap
from ..parameters import ParamOrGroup, ParamGroup, PassThru, TriFlag
from .restructured_text import RstTable
from .utils import format_help_entry, _should_add_default

if TYPE_CHECKING:
    from ..utils import Bool


BoolFormatterMap = Dict[bool, Callable[[str], str]]


class ParamHelpFormatter:
    _param_cls_fmt_cls_map = {}
    required_formatter_map: BoolFormatterMap = {False: '[{}]'.format}

    def __init_subclass__(cls, param_cls: Type[ParamOrGroup] = None):  # noqa
        if param_cls is not None:
            cls._param_cls_fmt_cls_map[param_cls] = cls

    @classmethod
    def for_param_cls(cls, param_cls: Type[ParamOrGroup]):
        try:
            return cls._param_cls_fmt_cls_map[param_cls]
        except KeyError:
            pass

        for p_cls, f_cls in reversed(tuple(cls._param_cls_fmt_cls_map.items())):  # tuple() only for 3.7 compatibility
            if issubclass(param_cls, p_cls):
                return f_cls

        return ParamHelpFormatter

    def __new__(cls, param: ParamOrGroup):
        fmt_cls = cls.for_param_cls(param.__class__) if cls is ParamHelpFormatter else cls
        return super().__new__(fmt_cls)

    def __init__(self, param: ParamOrGroup):
        self.param = param

    def wrap_usage(self, text: str) -> str:
        try:
            return self.required_formatter_map[self.param.required](text)
        except KeyError:
            return text

    def format_metavar(self) -> str:
        param = self.param
        if param.choices:
            return '{{{}}}'.format(ctx.config.choice_delim.join(map(str, param.choices)))
        elif param.metavar:
            return param.metavar
        t = param.type
        if t is not None:
            try:
                return t.format_metavar(ctx.config.choice_delim)
            except Exception:  # noqa  # pylint: disable=W0703
                pass

        if ctx.config.use_type_metavar and t is not None:
            try:
                name = t.__name__
            except AttributeError:
                pass
            else:
                if name != '<lambda>':
                    return name.upper()

        return param.name.upper()

    def format_basic_usage(self) -> str:
        """Format the Parameter for use in the ``usage:`` line"""
        return self.wrap_usage(self.format_usage(True))

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        """Format the Parameter for use in both the ``usage:`` line and in the list of Parameters"""
        return self.format_metavar()

    def format_description(self, rst: Bool = False) -> str:
        param = self.param
        description = param.help or ''
        if _should_add_default(param.default, description, param.show_default):
            pad = ' ' if description else ''
            quote = '``' if rst else ''
            description += f'{pad}(default: {quote}{param.default!r}{quote})'

        return description

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        usage = self.format_usage(include_meta=True, full=True)
        description = self.format_description()
        return format_help_entry(usage, description, tw_offset=tw_offset, prefix=prefix)

    def rst_row(self) -> Tuple[str, str]:
        usage = self.format_usage(include_meta=True, full=True)
        return f'``{usage}``', self.format_description(rst=True)


class PositionalHelpFormatter(ParamHelpFormatter, param_cls=BasePositional):
    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        metavar = self.format_metavar()
        return metavar if not full or self.param.nargs == 1 else f'{metavar} [{metavar} ...]'


class OptionHelpFormatter(ParamHelpFormatter, param_cls=BaseOption):
    def _format_usage_metavar(self) -> str:
        metavar = self.format_metavar()
        if 0 in self.param.nargs:
            metavar = f'[{metavar}]'
        return metavar

    def format_usage_parts(self, delim: str = ', ') -> Union[str, Tuple[str, ...]]:
        param: BaseOption = self.param
        opts = param.option_strs
        if param.nargs == 0:
            return delim.join(opts.option_strs())

        metavar = self._format_usage_metavar()
        option_strs = tuple(opts.option_strs())
        usage_iter = (f'{opt} {metavar}' for opt in option_strs)
        options = len(option_strs)
        if options > 1 and (options * len(metavar) + 2) > max(78, ctx.terminal_width - 2) / 2:
            last = options - 1
            return tuple(f'{us}{delim}' if i < last else us for i, us in enumerate(usage_iter))

        return delim.join(usage_iter)

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        if full:
            parts = self.format_usage_parts(delim)
            return parts if isinstance(parts, str) else ''.join(parts)

        param: BaseOption = self.param
        opt = param.option_strs.display_long[0]
        if not include_meta or param.nargs == 0:
            return opt
        return f'{opt} {self._format_usage_metavar()}'

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        usage = self.format_usage_parts()
        description = self.format_description()
        return format_help_entry(usage, description, tw_offset=tw_offset, prefix=prefix)


class TriFlagHelpFormatter(OptionHelpFormatter, param_cls=TriFlag):
    def format_usage_parts(self, delim: str = ', ') -> Union[str, Tuple[str, ...]]:
        opts = self.param.option_strs
        primary = delim.join(opts.primary_option_strs())
        alts = delim.join(opts.alt_option_strs())
        return primary, alts

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        if full:
            return '{} | {}'.format(*self.format_usage_parts(delim))
        else:
            opts = self.param.option_strs
            return f'{opts.display_long_primary[0]} | {opts.display_long_alt[0]}'


class ChoiceMapHelpFormatter(ParamHelpFormatter, param_cls=ChoiceMap):
    def format_metavar(self) -> str:
        param = self.param
        if param.choices:
            return '{{{}}}'.format(ctx.config.choice_delim.join(map(str, filter(None, param.choices))))
        else:
            return param.metavar or param.name.upper()

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.format_metavar()

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        param: ChoiceMap = self.param
        usage = self.format_usage()
        help_entry = format_help_entry(usage, param.description, 2, tw_offset=tw_offset, prefix=prefix)

        # TODO: Combine choices/aliases that point to the same target sub Command
        parts = [f'{prefix}{param.title or param._default_title}:', help_entry]
        for choice in param.choices.values():
            parts.append(choice.format_help(lpad=4, tw_offset=tw_offset))

        parts.append(prefix.rstrip())
        return '\n'.join(parts)

    def rst_table(self) -> RstTable:
        param = self.param
        table = RstTable(param.title or param._default_title, param.description)
        for choice in param.choices.values():
            usage = choice.format_usage()
            table.add_row(f'``{usage}``', choice.help)
        return table


class PassThruHelpFormatter(ParamHelpFormatter, param_cls=PassThru):
    required_formatter_map = {True: '-- {}'.format, False: '[-- {}]'.format}


class GroupHelpFormatter(ParamHelpFormatter, param_cls=ParamGroup):  # noqa  # pylint: disable=W0223
    required_formatter_map: BoolFormatterMap = {True: '{{{}}}'.format, False: '[{}]'.format}

    def _get_choice_delim(self) -> str:
        param: ParamGroup = self.param
        if param.mutually_dependent:
            return ' + '
        elif param.mutually_exclusive:
            return ' | '
        else:
            return ', '

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        choice_delim = self._get_choice_delim()
        choices = choice_delim.join(mem.formatter.format_usage(include_meta, full, delim) for mem in self.param.members)
        return self.wrap_usage(choices)

    def format_description(self, rst: Bool = False) -> str:
        group = self.param
        if not group.description and not group._name:
            if ctx.config.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
                return 'Mutually {} options'.format('exclusive' if group.mutually_exclusive else 'dependent')
            else:
                return 'Optional arguments'
        else:
            description = group.description or f'{group.name} options'
            if ctx.config.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
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

    def format_help(self, prefix: str = '', tw_offset: int = 0, clean: Bool = True) -> str:
        """
        Prepare the help text for this group.

        :param prefix: Prefix to add to every line (primarily intended for use with nested groups)
        :param tw_offset: Terminal width offset for text width calculations
        :param clean: If this group only contains other groups or Action or SubCommand parameters, then omit the
          description.
        :return: The formatted help text.
        """
        description = self.format_description()
        parts = [f'{prefix}{description}:']

        if ctx.config.show_group_tree:
            spacer = prefix + self._get_spacer()
            tw_offset += 2
        else:
            spacer = prefix

        nested, params = 0, 0
        for member in self.param.members:
            if not member.show_in_help:
                continue

            if isinstance(member, (ChoiceMap, ParamGroup)):
                nested += 1
                parts.append(spacer.rstrip())  # Add space for readability
            else:
                params += 1
            parts.append(member.formatter.format_help(prefix=spacer, tw_offset=tw_offset))

        if clean and nested and not params:
            parts = parts[2:]  # remove description and the first spacer

        if not parts[-1].endswith('\n'):  # ensure a new line separates sections, but avoid extra lines
            parts.append(spacer.rstrip())

        return '\n'.join(parts)

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
