"""
Parameter usage / help text formatters

:author: Doug Skrypa
"""
# pylint: disable=W0613

from __future__ import annotations

from typing import TYPE_CHECKING, Type, Callable, Iterator, Iterable, Tuple, Dict

try:
    from functools import cached_property
except ImportError:
    from ..compat import cached_property

from ..config import SubcommandAliasHelpMode
from ..context import ctx
from ..core import get_config
from ..parameters.base import BasePositional, BaseOption
from ..parameters.choice_map import ChoiceMap, Choice
from ..parameters import ParamGroup, PassThru, TriFlag
from .restructured_text import RstTable
from .utils import format_help_entry, _should_add_default

if TYPE_CHECKING:
    from ..typing import Bool, ParamOrGroup, OptStr

BoolFormatterMap = Dict[bool, Callable[[str], str]]


class ParamHelpFormatter:
    __slots__ = ('param',)
    _param_cls_fmt_cls_map = {}
    required_formatter_map: BoolFormatterMap = {False: '[{}]'.format}

    def __init_subclass__(cls, param_cls: Type[ParamOrGroup] = None, **kwargs):
        super().__init_subclass__(**kwargs)
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

    def maybe_wrap_usage(self, text: str) -> str:
        """
        Wraps the provided text in parentheses / brackets / etc based on whether the associated Parameter is required,
        if supported.
        """
        try:
            return self.required_formatter_map[self.param.required](text)
        except KeyError:
            return text

    def format_metavar(self) -> str:
        param = self.param
        if param.metavar:
            return param.metavar
        t = param.type
        if t is not None:
            try:
                config = ctx.config
                metavar = t.format_metavar(config.choice_delim, config.sort_choices)
            except Exception:  # noqa  # pylint: disable=W0703
                pass
            else:
                if metavar is not NotImplemented:
                    return metavar

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
        return self.maybe_wrap_usage(self.format_usage(True))

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        """Format the Parameter for use in both the ``usage:`` line and in the list of Parameters"""
        return self.format_metavar()

    def iter_usage_parts(self, include_meta: Bool = False, full: Bool = False) -> Iterator[str]:
        yield self.format_usage(include_meta=include_meta, full=full)

    def format_description(self, rst: Bool = False, description: str = None) -> str:
        param = self.param
        if description is None:
            description = param.help or ''
        if _should_add_default(param.default, description, param.show_default):
            pad = ' ' if description else ''
            quote = '``' if rst else ''
            description += f'{pad}(default: {quote}{param.default!r}{quote})'

        return description

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        usage_iter = self.iter_usage_parts(include_meta=True, full=True)
        description = self.format_description()
        return format_help_entry(usage_iter, description, prefix, tw_offset)

    # region RST

    def rst_usage(self) -> str:
        usage = self.format_usage(include_meta=True, full=True)
        return f'``{usage}``'

    def rst_row(self) -> Tuple[str, str]:
        """Returns a tuple of (usage, description)"""
        return self.rst_usage(), self.format_description(rst=True)

    def rst_rows(self) -> Iterator[Tuple[str, str]]:
        yield self.rst_row()

    # endregion


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

    def iter_usage_parts(self, include_meta: Bool = False, full: Bool = False) -> Iterator[str]:
        param: BaseOption = self.param
        opts = param.option_strs
        if param.nargs == 0:
            yield from opts.option_strs()
        else:
            metavar = self._format_usage_metavar()
            yield from (f'{opt} {metavar}' for opt in opts.option_strs())

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        if full:
            return delim.join(self.iter_usage_parts())

        param: BaseOption = self.param
        opt = param.option_strs.display_long[0]
        if not include_meta or param.nargs == 0:
            return opt
        return f'{opt} {self._format_usage_metavar()}'

    def rst_usage(self) -> str:
        return ', '.join(f'``{part}``' for part in self.iter_usage_parts())


class TriFlagHelpFormatter(OptionHelpFormatter, param_cls=TriFlag):
    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        opts = self.param.option_strs
        if full:
            primary = delim.join(opts.primary_option_strs())
            alts = delim.join(opts.alt_option_strs())
            return f'{primary} | {alts}'
        else:
            return f'{opts.display_long_primary[0]} | {opts.display_long_alt[0]}'

    def format_description(self, rst: Bool = False, alt: bool = False) -> str:
        if not alt:
            return super().format_description(rst=rst)
        alt_help = self.param.alt_help
        if alt_help:
            return super().format_description(rst=rst, description=alt_help)
        return ''

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        opts = self.param.option_strs
        primary = format_help_entry(opts.primary_option_strs(), self.format_description(), prefix, tw_offset)
        alt_desc = self.format_description(alt=True)
        alt_entry = format_help_entry(opts.alt_option_strs(), alt_desc, prefix, tw_offset, lpad=2 if alt_desc else 4)
        return f'{primary}\n{alt_entry}'

    def rst_rows(self) -> Iterator[Tuple[str, str]]:
        opts = self.param.option_strs
        for alt in (False, True):
            usage = ', '.join(f'``{part}``' for part in opts.option_strs(alt))
            description = self.format_description(rst=True, alt=alt)
            yield usage, description


class ChoiceMapHelpFormatter(ParamHelpFormatter, param_cls=ChoiceMap):
    @cached_property
    def choice_groups(self) -> Iterable[ChoiceGroup]:
        return ChoiceGroup.group_choices(self.param.choices.values())

    def format_metavar(self) -> str:
        param: ChoiceMap = self.param
        if param.choices:
            config = ctx.config
            choices = (str(c) for c in (c.choice for cg in self.choice_groups for c in cg.choices) if c is not None)
            if config.sort_choices:
                choices = sorted(choices)
            return '{{{}}}'.format(config.choice_delim.join(choices))
        else:
            return param.metavar or param.name.upper()

    def format_usage(self, include_meta: Bool = False, full: Bool = False, delim: str = ', ') -> str:
        return self.format_metavar()

    def format_help(self, prefix: str = '', tw_offset: int = 0) -> str:
        param: ChoiceMap = self.param
        help_entry = format_help_entry(self.iter_usage_parts(), param.description, prefix, tw_offset, lpad=2)
        choices = self._format_choices(prefix, tw_offset)
        if ctx.config.sort_choices:
            choices = sorted(choices)

        parts = (
            f'{prefix}{param.title or param._default_title}:',
            help_entry,
            *choices,
            prefix.rstrip(),
        )
        return '\n'.join(parts)

    def _format_choices(self, prefix: str = '', tw_offset: int = 0) -> Iterator[str]:
        mode = ctx.config.cmd_alias_mode or SubcommandAliasHelpMode.ALIAS
        for choice_group in self.choice_groups:
            yield from choice_group.format(mode, tw_offset, prefix)

    def rst_table(self) -> RstTable:
        rows = self._format_rst_rows()
        if ctx.config.sort_choices:
            rows = sorted(rows)

        param = self.param
        table = RstTable(param.title or param._default_title, param.description)
        table.add_rows(rows)
        return table

    def _format_rst_rows(self) -> Iterator[Tuple[str, OptStr]]:
        mode = ctx.config.cmd_alias_mode or SubcommandAliasHelpMode.ALIAS
        for choice_group in self.choice_groups:
            for choice, usage, description in choice_group.prepare(mode):
                yield f'``{usage}``', description


class ChoiceGroup:
    """
    A group of :class:`.Choice` objects from a given :class:`~.choice_map.ChoiceMap` that point to the same target.
    The first discovered Choice for a given target is considered the canonical one.  Subsequent Choices for that target
    are considered aliases.

    Used for formatting help text based on the configured :attr:`.CommandConfig.cmd_alias_mode`.
    """

    __slots__ = ('choice_strs', 'choices')

    def __init__(self, choice: Choice):
        choice_str = choice.choice
        self.choices = [choice]
        self.choice_strs = [choice_str] if choice_str else []

    @classmethod
    def group_choices(cls, choices: Iterable[Choice]) -> Iterable[ChoiceGroup]:
        """
        Processes the given Choices to group them by target and configured help text.  If two choices have the same
        target but different help text values, then they are considered different, so they are not grouped together.

        :param choices: The :class:`.Choice` objects that may contain aliases of each other.
        :return: The :class:`.ChoiceGroup` objects containing the grouped Choices.
        """
        target_choice_map = {}
        for n, choice in enumerate(choices):
            key = (choice.target, n if choice.local else None, choice.help)
            try:
                target_choice_map[key].add(choice)
            except KeyError:
                target_choice_map[key] = cls(choice)

        return target_choice_map.values()

    def add(self, choice: Choice):
        self.choices.append(choice)
        choice_str = choice.choice
        if choice_str:
            self.choice_strs.append(choice_str)

    def format(self, default_mode: SubcommandAliasHelpMode, tw_offset: int = 0, prefix: str = '') -> Iterator[str]:
        """
        :param default_mode: The default :class:`.SubcommandAliasHelpMode` to use if no mode was explicitly configured.
        :param tw_offset: Terminal width offset for text width calculations.
        :param prefix: Prefix to add to every line (primarily intended for use with nested groups).
        :return: Generator that yields formatted help text entries (strings) for the Choices in this group.
        """
        for choice, usage, description in self.prepare(default_mode):
            yield format_help_entry((usage,), description, lpad=4, tw_offset=tw_offset, prefix=prefix)

    def prepare(self, default_mode: SubcommandAliasHelpMode) -> Iterator[Tuple[Choice, OptStr, OptStr]]:
        """
        Prepares the choice values and descriptions to use for each Choice in this group based on the configured alias
        mode.

        :param default_mode: The default :class:`.SubcommandAliasHelpMode` to use if no mode was explicitly configured.
        :return: Generator that yields 3-tuples containing the :class:`.Choice` object, the choice string value, and
          the help text / description for that choice / alias.
        """
        first = self.choices[0]
        config = get_config(first.target)
        # If it's not a Command, get_config will return None.  If it is a Command, then it will use its config.  If the
        # alias mode is not set on that target Command, but it is set on its parent, then this will use that parent's
        # setting.
        if config:
            mode = config.cmd_alias_mode or default_mode
        else:
            mode = default_mode

        if mode == SubcommandAliasHelpMode.ALIAS:
            yield from self.prepare_aliases()
        elif mode == SubcommandAliasHelpMode.REPEAT:
            yield from self.prepare_repeated()
        elif mode == SubcommandAliasHelpMode.COMBINE:
            yield self.prepare_combined()
        else:  # Treat as a format string
            yield from self.prepare_aliases(mode)

    def prepare_combined(self) -> Tuple[Choice, OptStr, OptStr]:
        """
        Prepare this group's Choices for inclusion in help text / documentation by combining all aliases into a single
        entry.
        """
        first, choice_strs = self.choices[0], self.choice_strs
        try:
            usage, *additional = choice_strs
        except ValueError:  # choice_strs is empty
            return first, first.format_usage(), first.help

        if additional:
            usage = '{{{}}}'.format('|'.join(choice_strs))

        return first, usage, first.help

    def prepare_aliases(self, format_str: str = 'Alias of: {choice}') -> Iterator[Tuple[Choice, OptStr, OptStr]]:
        """
        Prepare this group's Choices for inclusion in help text / documentation using an alternate description for
        aliases.

        Variables supported in the :paramref:`.format_str`:

        - ``{choice}``: The first ("canonical") choice string for this group
        - ``{alias}``: The alias choice string
        - ``{help}``: The original help text for this Choice / group

        To append a suffix to alias descriptions instead of the default prefix, a mode / format string like the
        following could be used::

            cmd_alias_mode='{help} [Alias of: {choice}]'

        :param format_str: The :ref:`format string <python:formatstrings>` to use as the help text / description for
          aliases.
        :return: Generator that yields 3-tuples containing the :class:`.Choice` object, the choice string value, and
          the help text / description for that choice / alias.
        """
        first = self.choices[0]
        try:
            first_str, *choice_strs = self.choice_strs
        except ValueError:  # choice_strs is empty
            yield first, first.format_usage(), first.help
        else:
            help_str = first.help
            yield first, first_str, help_str
            for choice_str in choice_strs:
                yield first, choice_str, format_str.format(choice=first_str, alias=choice_str, help=help_str)

    def prepare_repeated(self) -> Iterator[Tuple[Choice, OptStr, OptStr]]:
        """
        Prepare this group's Choices for inclusion in help text / documentation with no modifications.  Choices that
        are considered aliases are simply repeated as if they were not aliases.
        """
        for choice in self.choices:
            yield choice, choice.format_usage(), choice.help


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
        members = choice_delim.join(mem.formatter.format_usage(include_meta, full, delim) for mem in self.param.members)
        return self.maybe_wrap_usage(choice_delim.join(members))

    def format_description(self, rst: Bool = False, description: str = None) -> str:
        if description:
            return description
        group = self.param
        if group.description or group._name:
            description = group.description or f'{group.name} options'
            if ctx.config.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
                description += f' (mutually {"exclusive" if group.mutually_exclusive else "dependent"})'
            return description
        elif ctx.config.show_group_type and (group.mutually_exclusive or group.mutually_dependent):
            return f'Mutually {"exclusive" if group.mutually_exclusive else "dependent"} options'

        adjective = 'Required' if group.required else 'Other' if group.contains_required else 'Optional'
        return f'{adjective} arguments'

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
                formatter = member.formatter
                try:
                    sub_table: RstTable = formatter.rst_table()  # noqa
                except AttributeError:
                    table.add_rows(formatter.rst_rows())
                    # table.add_row(*formatter.rst_row())
                else:
                    sub_table.show_title = False
                    table.add_row(sub_table.title, str(sub_table))

        return table
