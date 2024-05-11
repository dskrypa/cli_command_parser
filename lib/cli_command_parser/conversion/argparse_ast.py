from __future__ import annotations

import ast
import logging
import sys
from argparse import ArgumentParser
from ast import AST, Assign, Call, withitem
from functools import cached_property, partial
from inspect import BoundArguments, Signature
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Collection, Generic, Iterator, Type, TypeVar, Union

from .argparse_utils import ArgumentParser as _ArgumentParser, SubParsersAction as _SubParsersAction
from .utils import get_name_repr, iter_module_parents, unparse

if TYPE_CHECKING:
    from cli_command_parser.typing import PathLike

    from .visitor import TrackedRef, TrackedRefMap

__all__ = ['ParserArg', 'ArgGroup', 'MutuallyExclusiveGroup', 'AstArgumentParser', 'SubParser', 'Script']
log = logging.getLogger(__name__)

InitNode = Union[Call, Assign, withitem]
OptCall = Union[Call, None]
ParserCls = Type['AstArgumentParser']
ParserObj = TypeVar('ParserObj', bound='AstArgumentParser')
RepresentedCallable = TypeVar('RepresentedCallable', bound=Callable)
AC = TypeVar('AC', bound='AstCallable')
D = TypeVar('D')
_NotSet = object()


class Script:
    _parser_classes = {}
    path: Union[Path, None]

    def __init__(self, src_text: str, smart_loop_handling: bool = True, path: PathLike = None):
        self.smart_loop_handling = smart_loop_handling
        self._parsers = []
        self.path = Path(path) if path else None
        self.src_text = src_text
        parse_args = (self.src_text, self.path.as_posix()) if self.path else (self.src_text,)
        self.root_node = ast.parse(*parse_args)

    def __repr__(self) -> str:
        parsers = len(self.parsers)
        location = f' @ {self.path.as_posix()}' if self.path else ''
        return f'<{self.__class__.__name__}[{parsers=}{location}]>'

    @property
    def mod_cls_to_ast_cls_map(self) -> dict[str, dict[str, ParserCls]]:
        return self._parser_classes

    @classmethod
    def _register_parser(cls, module: str, name: str, ast_cls: ParserCls):
        # Identify package-level exports that may have been defined for a custom ArgumentParser subclass
        modules = [module, *(parent for parent in iter_module_parents(module) if name in vars(sys.modules[parent]))]
        for module in modules:
            log.debug(f'Registering {module}.{name} -> {ast_cls}')
            cls._parser_classes.setdefault(module, {})[name] = ast_cls

    @classmethod
    def register_parser(cls, ast_cls: ParserCls):
        real_cls = ast_cls.represents
        cls._register_parser(real_cls.__module__, real_cls.__name__, ast_cls)
        return ast_cls

    def add_parser(self, ast_cls: ParserCls, node: InitNode, call: OptCall, tracked_refs: TrackedRefMap) -> ParserObj:
        parser = ast_cls(node, self, tracked_refs, call)
        self._parsers.append(parser)
        return parser

    @cached_property
    def parsers(self) -> list[ParserObj]:
        from .visitor import ScriptVisitor, TrackedRef  # noqa: F811

        track_refs = (TrackedRef('argparse.REMAINDER'), TrackedRef('argparse.SUPPRESS'))
        visitor = ScriptVisitor(self.smart_loop_handling, track_refs=track_refs)
        for module, name_cls_map in self.mod_cls_to_ast_cls_map.items():
            for name, ast_cls in name_cls_map.items():
                visitor.track_callable(module, name, partial(self.add_parser, ast_cls))

        visitor.visit(self.root_node)
        return self._parsers


# region Decorators & Descriptors


class visit_func:
    """A method that can be called by an AST visitor."""

    __slots__ = ('func',)

    def __init__(self, func):
        self.func = func

    def __set_name__(self, owner: Type[AstCallable], name: str):
        if owner._add_visit_func(name):  # This check is only to enable a low-value unit test...
            setattr(owner, name, self.func)  # There's no need to keep the descriptor - replace self with func

    def __get__(self, instance, owner):
        # This will never actually be called, but it makes PyCharm happy
        return self if instance is None else partial(self.func, instance)


class AddVisitedChild(Generic[AC]):
    """Simplifies the definition of an add_child method that can be called by an AST visitor, where possible."""

    __slots__ = ('child_cls', 'list_attr')

    def __init__(self, child_cls: Type[AC], attr: str):
        self.child_cls = child_cls
        self.list_attr = attr

    def __set_name__(self, owner: Type[ArgCollection], name: str):
        owner._add_visit_func(name)

    def __get__(self, instance: ArgCollection, owner) -> Callable[[InitNode, Call, TrackedRefMap], AC]:
        if instance is None:
            return self  # noqa
        return partial(instance._add_child, self.child_cls, getattr(instance, self.list_attr))  # noqa


# endregion


class AstCallable:
    represents: RepresentedCallable
    visit_funcs = set()
    _sig: Signature | None = None

    @classmethod
    def _add_visit_func(cls, name: str) -> bool:
        try:
            parent_visit_funcs = cls.__base__.visit_funcs  # noqa
        except AttributeError:
            pass
        else:  # Note: __init_subclass__ is called after __set_name__ is called for members
            if parent_visit_funcs is cls.visit_funcs:
                cls.visit_funcs = cls.visit_funcs.copy()
        cls.visit_funcs.add(name)
        return True

    def __init_subclass__(cls, represents: RepresentedCallable = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if represents:
            cls.represents = represents
            cls._sig = None

    def __init__(self, node: InitNode, parent: AstCallable | Script, tracked_refs: TrackedRefMap, call: Call = None):
        self.init_node = node
        if not call:
            call = node.value if isinstance(node, Assign) else node  # type: Call
        self.call_node = call
        self.call_args = call.args
        self.call_kwargs = call.keywords
        self._tracked_refs = tracked_refs
        self.parent = parent

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{self.init_call_repr()}]>'

    def get_tracked_refs(self, module: str, name: str, default: D = _NotSet) -> Union[set[str], D]:
        for tracked_ref, refs in self._tracked_refs.items():
            if tracked_ref.module == module and tracked_ref.name == name:
                return refs
        if default is not _NotSet:
            return default
        raise KeyError(f'No tracked ref found for {module}.{name}')

    # region Initialization Call

    @classmethod
    def _signature(cls) -> Signature:
        if not cls._sig:
            cls._sig = Signature.from_callable(cls.represents)
        return cls._sig

    @property
    def signature(self) -> Signature:
        return self._signature()

    @cached_property
    def init_func_name(self) -> str:
        """The name or alias of the function/callable that was used to initialize this object"""
        return get_name_repr(self.call_node.func)

    @cached_property
    def _init_func_bound(self) -> BoundArguments:
        args = self.call_args if isinstance(self.represents, type) else ('self', *self.call_args)
        return self.signature.bind(*args, **{kw.arg: kw.value for kw in self.call_kwargs})

    @cached_property
    def init_func_args(self) -> list[str]:
        try:
            args = self._init_func_bound.args[1:]
        except (TypeError, AttributeError):  # No represents func
            args = self.call_args
        return [unparse(arg) for arg in args]

    @cached_property
    def init_func_raw_kwargs(self) -> dict[str, AST]:
        try:
            kwargs = self._init_func_bound.arguments
        except (TypeError, AttributeError):  # No represents func
            return {kw.arg: kw.value for kw in self.call_kwargs}
        else:
            kwargs = kwargs.copy()
            kwargs.pop('self', None)
            if isinstance(kwargs.get('args'), tuple):
                kwargs.pop('args')
            if isinstance(kwargs.get('kwargs'), dict):
                kwargs.update(kwargs.pop('kwargs'))
            return kwargs

    def _init_func_kwargs(self) -> dict[str, str]:
        return {key: unparse(val) for key, val in self.init_func_raw_kwargs.items()}

    @cached_property
    def init_func_kwargs(self) -> dict[str, str]:
        return self._init_func_kwargs()

    def init_call_repr(self) -> str:
        arg_str = ', '.join(self.init_func_args)
        if kw_str := ', '.join(f'{k}={v}' for k, v in self.init_func_kwargs.items()):
            arg_str = kw_str if not arg_str else (arg_str + ', ' + kw_str)
        return f'{self.init_func_name}({arg_str})'

    # endregion

    def pprint(self, indent: int = 0):
        print(f'{" " * indent} - {self!r}')


# region Stdlib Argparse Wrappers


class ParserArg(AstCallable, represents=ArgumentParser.add_argument):
    parent: ArgCollection


class ArgCollection(AstCallable):
    parent: ArgCollection | Script
    _children = ('args', 'groups')
    args: list[ParserArg]
    groups: list[ArgGroup]
    add_argument = AddVisitedChild(ParserArg, 'args')

    def __init_subclass__(cls, children: Collection[str] = (), **kwargs):
        super().__init_subclass__(**kwargs)
        if children:
            cls._children = (*cls._children, *children)

    def __init__(self, node: InitNode, parent: AstCallable | Script, tracked_refs: TrackedRefMap, call: Call = None):
        super().__init__(node, parent, tracked_refs, call)
        self.args = []
        self.groups = []

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: ``{self.init_call_repr()}``>'

    def _add_child(self, cls: Type[AC], container: list[AC], node: InitNode, call: Call, refs: TrackedRefMap) -> AC:
        child = cls(node, self, refs, call)
        container.append(child)
        return child

    @visit_func
    def add_mutually_exclusive_group(self, node: InitNode, call: Call, tracked_refs: TrackedRefMap):
        return self._add_child(MutuallyExclusiveGroup, self.groups, node, call, tracked_refs)

    @visit_func
    def add_argument_group(self, node: InitNode, call: Call, tracked_refs: TrackedRefMap):
        return self._add_child(ArgGroup, self.groups, node, call, tracked_refs)

    def grouped_children(self) -> Iterator[tuple[Type[AC], list[AC]]]:
        yield ParserArg, self.args
        yield ArgGroup, self.groups

    # region Output Methods

    def pprint(self, indent: int = 0):
        print(f'{" " * indent} + {self!r}:')
        indent += 3
        for attr in self._children:
            if values := getattr(self, attr):
                for value in values:
                    value.pprint(indent)

    # endregion


class ArgGroup(ArgCollection, represents=_ArgumentParser.add_argument_group):
    pass


class MutuallyExclusiveGroup(ArgGroup, represents=_ArgumentParser.add_mutually_exclusive_group):
    pass


class SubparsersAction(AstCallable, represents=_ArgumentParser.add_subparsers):
    parent: ParserObj

    @visit_func
    def add_parser(self, node: InitNode, call: Call, tracked_refs: TrackedRefMap):
        sub_parser = self.parent._add_subparser(node, call, tracked_refs)
        sub_parser.sp_parent = self
        return sub_parser


@Script.register_parser
class AstArgumentParser(ArgCollection, represents=ArgumentParser, children=('sub_parsers',)):
    sub_parsers: list[SubParser]
    add_subparsers = AddVisitedChild(SubparsersAction, '_subparsers_actions')

    def __init__(self, node: InitNode, parent: AstCallable | Script, tracked_refs: TrackedRefMap, call: Call = None):
        super().__init__(node, parent, tracked_refs, call)
        self._subparsers_actions = []
        # Note: sub_parsers aren't included in grouped_children since they need different handling during conversion
        self.sub_parsers = []

    def __repr__(self) -> str:
        sub_parsers = len(self.sub_parsers)
        return f'<{self.__class__.__name__}[{sub_parsers=}]: ``{self.init_call_repr()}``>'

    def _add_subparser(self, node: InitNode, call: Call, tracked_refs: TrackedRefMap, sub_parser_cls: ParserCls = None):
        # Using default of None since the class hasn't been defined at the time it would need to be set as default
        return self._add_child(sub_parser_cls or SubParser, self.sub_parsers, node, call, tracked_refs)


class SubParser(AstArgumentParser, represents=_SubParsersAction.add_parser):
    sp_parent: SubparsersAction

    @cached_property
    def init_func_kwargs(self) -> dict[str, str]:
        kwargs = self.sp_parent.init_func_kwargs.copy()
        kwargs.update(self._init_func_kwargs())
        return kwargs


# endregion
