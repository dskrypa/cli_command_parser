from __future__ import annotations

import keyword
import logging
from abc import ABC, abstractmethod
from ast import literal_eval, Attribute, Name, GeneratorExp, Subscript, DictComp, ListComp, SetComp
from dataclasses import dataclass, fields
from itertools import count
from typing import TYPE_CHECKING, Union, Optional, Iterator, Iterable, Type, TypeVar, Generic, List, Tuple

from cli_command_parser.compat import cached_property
from cli_command_parser.nargs import Nargs
from .argparse_ast import AC, ParserArg, ArgGroup, MutuallyExclusiveGroup, AstArgumentParser, Script
from .utils import collection_contents, unparse

if TYPE_CHECKING:
    from cli_command_parser.typing import OptStr
    from .argparse_ast import ArgCollection

__all__ = ['convert_script']
log = logging.getLogger(__name__)

C = TypeVar('C', bound='Converter')

RESERVED = set(keyword.kwlist) | set(getattr(keyword, 'softkwlist', ('_', 'case', 'match')))  # soft was added in 3.9


def convert_script(script: Script) -> str:
    return ScriptConverter(script).convert()


class Converter(ABC):
    converts: Type[AC] = None
    _ac_converter_map = {}

    def __init_subclass__(cls, converts: Type[AC] = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if converts:
            cls.converts = converts
            cls._ac_converter_map[converts] = cls

    def __init__(self, ast_obj: Union[AC, Script], parent: Optional[Converter] = None):
        self.ast_obj = ast_obj
        self.parent = parent

    @classmethod
    def for_ast_callable(cls, ast_obj: Union[AC, Type[AC]]) -> Type[Converter]:
        if not isinstance(ast_obj, type):
            ast_obj = ast_obj.__class__
        try:
            return cls._ac_converter_map[ast_obj]
        except KeyError:
            pass
        for converts_cls, converter_cls in cls._ac_converter_map.items():
            if issubclass(ast_obj, converts_cls):
                return converter_cls
        raise TypeError(f'No Converter is registered for {ast_obj.__class__.__name__} objects')

    @classmethod
    def init_group(cls: Type[C], parent: CollectionConverter, ast_objs: List[AC]) -> ConverterGroup[C]:
        return ConverterGroup(parent, cls, [cls(ast_obj, parent) for ast_obj in ast_objs])

    def convert(self, indent: int = 0) -> str:
        return '\n'.join(self.format_lines(indent))

    @abstractmethod
    def format_lines(self, indent: int = 0) -> Iterator[str]:
        raise NotImplementedError


class ConverterGroup(Generic[C]):
    __slots__ = ('parent', 'member_type', 'members')

    def __init__(self, parent: CollectionConverter, member_type: Type[C], members: List[C]):
        self.parent = parent
        self.member_type = member_type
        self.members = members

    def __len__(self) -> int:
        return len(self.members)

    def __getitem__(self, index: int) -> C:
        return self.members[index]

    def __iter__(self) -> Iterator[C]:
        yield from self.members

    def format_all(self, indent: int = 0) -> Iterator[str]:
        for member in self.members:
            yield from member.format_lines(indent)


class ScriptConverter(Converter, converts=Script):
    def format_lines(self, indent: int = 0) -> Iterator[str]:
        # TODO: Filter to what is actually used
        yield (
            'from cli_command_parser import'
            ' Command, SubCommand, ParamGroup, Positional, Option, Flag, Counter, PassThru, main'
        )
        counter = count()
        for parser in self.ast_obj.parsers:
            yield from ParserConverter(parser, counter=counter).format_lines()


class CollectionConverter(Converter, ABC):
    ast_obj: ArgCollection
    parent: CollectionConverter | None
    _name_mode = None

    @cached_property
    def name_mode(self) -> str | None:
        return self._name_mode or (self.parent.name_mode if self.parent else None)

    @cached_property
    def grouped_children(self) -> List[ConverterGroup[ParamConverter | GroupConverter | Converter]]:
        return [self.for_ast_callable(cg_cls).init_group(self, cg) for cg_cls, cg in self.ast_obj.grouped_children()]

    def descendant_args(self) -> Iterator[ParamConverter]:
        for child_group in self.grouped_children:
            if not child_group.members:
                continue
            elif hasattr(child_group[0], 'descendant_args'):
                for child in child_group:
                    yield from child.descendant_args()
            elif isinstance(child_group[0], ParamConverter):
                yield from child_group

    def format_members(self, prefix: str, indent: int = 4) -> Iterator[str]:
        last = False
        for child_group in self.grouped_children:
            if last and child_group and issubclass(child_group.member_type, GroupConverter):
                yield ''
            yield from child_group.format_all(indent)
            last = bool(child_group)

        if not any(cg for cg in self.grouped_children):
            yield f'{prefix}    pass'


class ParserConverter(CollectionConverter, converts=AstArgumentParser):
    _auto_gen_disclaimer = '# This is an automatically generated name that should probably be updated'
    ast_obj: AstArgumentParser
    parent: ParserConverter | None

    def __init__(self, parser: AstArgumentParser, parent: ParserConverter = None, counter: count = None):
        super().__init__(parser, parent)
        self.counter = count() if counter is None else counter

    @cached_property
    def sub_parser_converters(self) -> List[ParserConverter]:
        return [self.__class__(sub_parser, self, self.counter) for sub_parser in self.ast_obj.sub_parsers]

    def descendant_args(self) -> Iterator[ParamConverter]:
        yield from super().descendant_args()
        for sp_converter in self.sub_parser_converters:
            yield from sp_converter.descendant_args()

    def format_lines(self, indent: int = 0) -> Iterator[str]:
        suffix = f'  {self._auto_gen_disclaimer}' if self.parent is None else ''
        # TODO: Add _init_command_ and/or main methods
        # TODO: If subparsers have no unique args, use action methods instead?
        yield '\n'
        yield f'class {self.name}({self._get_args()}):{suffix}'
        yield from self.format_members('')
        for sp_converter in self.sub_parser_converters:
            yield from sp_converter.format_lines()

    def _get_args(self) -> str:
        kwargs = self.ast_obj.init_func_kwargs.copy()
        # log.debug(f'Processing args for {kwargs}')
        kwargs['option_name_mode'] = self._name_mode
        if self.is_sub_parser:
            key, value = self._choices
            if key:
                kwargs[key] = value
        elif 'add_help' in kwargs and literal_eval_or_none(kwargs['add_help']) is True:
            kwargs.pop('add_help')

        cmd_args = CommandArgs.from_kwargs(**kwargs)
        return cmd_args.to_str(self.parent.name if self.parent else 'Command')

    @cached_property
    def is_sub_parser(self) -> bool:
        return self.parent is not None

    # region Name / CLI Choices

    @cached_property
    def name(self) -> str:
        return self._custom_name or f'Command{next(self.counter)}'

    @cached_property
    def _custom_name(self) -> OptStr:
        if not self.is_sub_parser:
            return None
        name = literal_eval_or_none(self.ast_obj.init_func_kwargs.get('name'))
        if not name or not name[0].isalpha():
            return None
        return name.title().replace(' ', '').replace('_', '').replace('-', '')

    @cached_property
    def _choices(self) -> Tuple[OptStr, OptStr]:
        if not self.is_sub_parser:
            return None, None
        name = self.ast_obj.init_func_kwargs.get('name')
        aliases = self.ast_obj.init_func_raw_kwargs.get('aliases')
        if not aliases:
            if name and (not self._custom_name or '-' in name or ' ' in name):
                return 'choice', name
            return None, None
        elif isinstance(aliases, (Attribute, Name, Subscript, GeneratorExp, DictComp, ListComp, SetComp)):
            value = unparse(aliases)  # noqa
            if name:
                return 'choices', f'({name}, *{value})'
            return 'choices', (f'tuple{value}' if isinstance(aliases, GeneratorExp) else value)
        else:
            parsed = collection_contents(aliases)
            values = [name, *parsed] if name else parsed
            if len(values) == 1:
                return 'choice', values[0]
            elif values:
                return 'choices', f'({", ".join(values)})'
            return None, None

    # endregion

    # region Member-Related Properties

    @cached_property
    def name_mode(self) -> str | None:
        return self._name_mode or (self.parent.name_mode if self.parent else None)

    @cached_property
    def _name_mode(self) -> str | None:
        if self.parent and self.parent._name_mode:
            return None
        name_modes = {pc._name_mode for pc in self.descendant_args() if pc.is_option and '_' in pc.attr_name}
        return next(iter(name_modes)) if len(name_modes) == 1 else None

    # endregion


class GroupConverter(CollectionConverter, converts=ArgGroup):
    ast_obj: ArgGroup

    def format_lines(self, indent: int = 4) -> Iterator[str]:
        prefix = ' ' * indent
        yield f'{prefix}with ParamGroup({self._get_args()}):'
        yield from self.format_members(prefix, indent + 4)

    def _get_args(self) -> str:
        # log.debug(f'Processing args for {self.ast_obj._init_func_bound}')
        description = self.ast_obj.init_func_kwargs.get('description')
        title = self.ast_obj.init_func_kwargs.get('title')
        if title:
            title_str = literal_eval(title)
            if title_str.lower().endswith(' options'):
                if description:
                    title = repr(title_str[:-7].rstrip())
                else:
                    description, title = title, None

        args = [title] if title else []
        if description:
            args.append(f'description={description}')
        if isinstance(self.ast_obj, MutuallyExclusiveGroup):
            args.append('mutually_exclusive=True')
        return ', '.join(args)


class ParamConverter(Converter, converts=ParserArg):
    ast_obj: ParserArg
    parent: CollectionConverter | None
    _counter = count()

    def __init__(self, arg: ParserArg, parent: CollectionConverter, num: int):
        super().__init__(arg, parent)
        self.num = num

    def __eq__(self, other: ParamConverter) -> bool:
        return self.ast_obj == other.ast_obj and self.num == other.num

    def __lt__(self, other: ParamConverter) -> bool:
        if self.is_positional and not other.is_positional:
            return True
        if self.is_pass_thru and not other.is_pass_thru:
            return False
        return self.num < other.num

    @classmethod
    def init_group(cls, parent: CollectionConverter, args: List[ParserArg]) -> ParamConverterGroup:
        return ParamConverterGroup(parent, cls, [cls(arg, parent, i) for i, arg in enumerate(args)])

    def format_lines(self, indent: int = 4) -> Iterator[str]:
        yield self.format(indent)

    def format(self, indent: int = 4) -> str:
        param_cls, args_obj = self.get_cls_and_kwargs()
        arg_str = args_obj.to_str(*self.get_pos_args())
        return f'{" " * indent}{self.attr_name} = {param_cls}({arg_str})'

    # region Naming

    @cached_property
    def attr_name(self) -> str:
        return self._attr_name.replace('-', '_')

    @cached_property
    def name_mode(self) -> str | None:
        return None if self.parent.name_mode else self._name_mode

    @cached_property
    def _name_mode(self) -> str | None:
        if not self.use_auto_long_opt_str:
            return None
        return "'_'" if '_' in self._attr_name else None

    @cached_property
    def _attr_name(self) -> str:
        return next(name for name in self._attr_name_candidates() if name not in RESERVED)

    def _attr_name_candidates(self) -> Iterator[str]:
        long, short, plain = self._grouped_opt_strs
        if self.is_positional or self.is_pass_thru:
            yield from plain
        if self.is_option or self.is_pass_thru:
            for group in (long, short):
                for opt in group:
                    opt = opt.lstrip('-')
                    if opt:
                        yield opt
        while True:
            yield f'param_{next(self._counter)}'

    # endregion

    # region Arg Processing

    @cached_property
    def cmd_option_strs(self) -> List[str]:
        if not self.is_option:
            return []
        long, short, plain = self._grouped_opt_strs
        return short if self.use_auto_long_opt_str else (long + short)

    @cached_property
    def use_auto_long_opt_str(self) -> bool:
        if not self.is_option:
            return False
        long, short, plain = self._grouped_opt_strs
        return len(long) == 1 and long[0][2:] == self._attr_name

    def get_pos_args(self) -> Iterable[str]:
        return (repr(arg) for arg in self.cmd_option_strs)

    def get_cls_and_kwargs(self) -> Tuple[str, BaseArgs]:
        kwargs = self.ast_obj.init_func_kwargs.copy()
        help_arg = kwargs.get('help')
        if help_arg and help_arg in self.ast_obj.get_tracked_refs('argparse', 'SUPPRESS', ()):
            kwargs.update({'hide': 'True', 'help': None})

        if self.is_pass_thru:
            return 'PassThru', PassThruArgs.from_kwargs(**kwargs)

        action = kwargs.pop('action', None)
        if action:
            action = literal_eval(action)

        if self.is_positional:
            if action and action not in ('store', 'append'):
                raise ConversionError(f'{self.ast_obj}: action={action!r} is not supported for Positional parameters')
            return 'Positional', ParamArgs.init_positional(action, **kwargs)
        elif self.is_option:
            kwargs['name_mode'] = self.name_mode
            if not action and 'const' in kwargs:
                action = 'append_const' if 'nargs' in kwargs else 'store_const'
            if action:
                if action in ('store_true', 'store_false', 'store_const', 'append_const'):
                    return 'Flag', FlagArgs.init_flag(action, **kwargs)
                elif action == 'count':
                    return 'Counter', FlagArgs.init_counter(**kwargs)
                elif action not in ('store', 'append'):
                    raise ConversionError(f'{self.ast_obj}: action={action!r} is not supported for Option parameters')

            return 'Option', OptionArgs.init_option(self.ast_obj, action, **kwargs)

        raise ConversionError(f'Unable to determine a suitable Parameter type for {self.ast_obj!r}')

    # endregion

    # region High Level Param Type

    @cached_property
    def is_pass_thru(self) -> bool:
        nargs = self.ast_obj.init_func_kwargs.get('nargs')
        if not nargs:
            return False
        return nargs in self.ast_obj.get_tracked_refs('argparse', 'REMAINDER', ())

    @cached_property
    def is_positional(self) -> bool:
        long, short, plain = self._grouped_opt_strs
        return plain and not long and not short

    @cached_property
    def is_option(self) -> bool:
        long, short, plain = self._grouped_opt_strs
        return (long or short) and not plain

    # endregion

    @cached_property
    def _grouped_opt_strs(self) -> Tuple[List[str], List[str], List[str]]:
        option_strs = (literal_eval(opt) for opt in self.ast_obj.init_func_args)
        long, short, plain = [], [], []
        for opt in option_strs:
            if opt.startswith('--'):
                long.append(opt)
            elif opt.startswith('-'):
                short.append(opt)
            else:
                plain.append(opt)
        return long, short, plain


class ParamConverterGroup(ConverterGroup[ParamConverter]):
    __slots__ = ()

    def __bool__(self) -> bool:
        return bool(self.members) or bool(getattr(self.parent.ast_obj, 'sub_parsers', None))

    def format_all(self, indent: int = 4) -> Iterator[str]:
        positionals, others = [], []
        i_converters = iter(sorted(self.members))
        for converter in i_converters:
            if converter.is_positional:
                positionals.append(converter)
            else:
                others.append(converter)
                others.extend(i_converters)

        for positional in positionals:
            yield from positional.format_lines(indent)

        sub_parsers = getattr(self.parent.ast_obj, 'sub_parsers', None)
        if sub_parsers:
            log.debug(f'Found sub_parsers={sub_parsers}')
            try:
                name = literal_eval(sub_parsers[0].init_func_kwargs['dest']).replace('-', '_')
            except (KeyError, ValueError):
                name = 'sub_cmd'
            else:
                if name in RESERVED:
                    name = 'sub_cmd'
            yield f'{" " * indent}{name} = SubCommand()'

        for other in others:
            yield from other.format_lines(indent)


# region Arg Containers


@dataclass
class BaseArgs:
    help: OptStr = None

    def _to_str(self, args: Tuple[str, ...], end_fields: List[str]) -> str:
        skip = set(end_fields)
        keys = [f.name for f in fields(self) if f.name not in skip] + end_fields
        kv_iter = ((key, getattr(self, key)) for key in keys)
        return ', '.join((*args, *(f'{key}={val}' for key, val in kv_iter if val is not None)))

    def to_str(self, *args: str) -> str:
        return self._to_str(args, ['help'])

    @classmethod
    def from_kwargs(cls, **kwargs):
        keys = set(f.name for f in fields(cls)).intersection(kwargs)
        filtered = {key: kwargs[key] for key in keys}
        help_str = filtered.get('help')
        if help_str:
            # log.debug(f'Processing {help_str=}')
            try:
                help_str = literal_eval(help_str)
            except ValueError:  # likely an f-string
                pass
            else:
                if help_str.endswith('(default: %(default)s)'):
                    help_str = help_str[:-22].rstrip()
                filtered['help'] = repr(help_str) if help_str else None

        return cls(**filtered)


@dataclass
class CommandArgs(BaseArgs):
    choice: OptStr = None
    choices: OptStr = None
    prog: OptStr = None
    usage: OptStr = None
    description: OptStr = None
    epilog: OptStr = None
    option_name_mode: OptStr = None
    add_help: OptStr = None
    docs_url: OptStr = None
    email: OptStr = None


# endregion


# region ParserArg Arg Containers


@dataclass
class ParamBaseArgs(BaseArgs):
    name: OptStr = None
    default: OptStr = None
    required: OptStr = None
    metavar: OptStr = None
    hide: OptStr = None

    def to_str(self, *args: str) -> str:
        return self._to_str(args, ['hide', 'help'])


@dataclass
class PassThruArgs(ParamBaseArgs):
    pass


@dataclass
class ParamArgs(ParamBaseArgs):
    action: OptStr = None
    type: OptStr = None
    nargs: OptStr = None
    choices: OptStr = None

    @classmethod
    def init_positional(cls, action: OptStr = None, nargs: OptStr = None, **kwargs):
        if nargs is not None:
            parsed = literal_eval_or_none(nargs)
            if parsed is not None:
                nargs_obj = Nargs(parsed)
                if action in ('store', None) and nargs_obj == 1:
                    action = nargs = None
            else:
                nargs_obj = None
        else:
            nargs_obj = Nargs(1)

        if nargs_obj is not None and action == 'append' and nargs_obj != Nargs(1):
            action = None
        return cls.from_kwargs(action=action, nargs=nargs, **kwargs)


@dataclass
class OptionArgs(ParamArgs):
    name_mode: OptStr = None

    @classmethod
    def init_option(cls, arg: ParserArg, action: OptStr = None, nargs: OptStr = None, const: OptStr = None, **kwargs):
        if const:
            log.warning(f'{arg}: ignoring const={const!r} - it is only supported for Flag and Counter parameters')

        if nargs == "'*'":
            nargs = "'+'"
        if action == 'append':
            if not nargs:
                log.debug(f"{arg}: using default nargs='+' because action={action!r} and no nargs value was provided")
                nargs = "'+'"
            action = None
        elif action == 'store':
            if nargs == '1':
                nargs = None
            action = None

        return cls.from_kwargs(action=repr(action) if action else None, nargs=nargs, **kwargs)


@dataclass
class FlagArgs(OptionArgs):
    const: OptStr = None

    @classmethod
    def init_flag(cls, action: str, const: OptStr = None, default: OptStr = None, **kwargs):
        values = {'store_true': ('True', 'False'), 'store_false': ('False', 'True')}
        try:
            value, opposite = values[action]
        except KeyError:
            if action == 'store_const':
                action = None
        else:
            if default == opposite:
                default = None
            action = None
            const = value if default else None

        kwargs['type'] = kwargs['nargs'] = None
        if action:
            action = repr(action)
        return cls.from_kwargs(action=action, const=const, default=default, **kwargs)

    @classmethod
    def init_counter(cls, const: OptStr = None, default: OptStr = None, **kwargs):
        kwargs['type'] = kwargs['nargs'] = kwargs['action'] = None
        kwargs['const'] = None if const == '1' else const
        kwargs['default'] = None if default == '0' else default
        return cls.from_kwargs(**kwargs)


# endregion


def literal_eval_or_none(expr: str) -> str | None:
    try:
        return literal_eval(expr)
    except ValueError:
        return None


class ConversionError(Exception):
    pass
