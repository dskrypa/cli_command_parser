from __future__ import annotations

import logging
from ast import NodeVisitor, AST, Assign, Call, For, Attribute, Name, Import, ImportFrom, expr
from collections import ChainMap, defaultdict
from functools import partial, wraps
from typing import Iterator, Union, Callable, Collection, Tuple, List, Dict, Set

from .argparse_ast import AstArgumentParser
from .utils import get_name_repr

__all__ = ['ScriptVisitor', 'TrackedRef']
log = logging.getLogger(__name__)

TrackedRefMap = Dict['TrackedRef', Set[str]]
_NoCall = object()


def scoped(func):
    @wraps(func)
    def _scoped_method(self: ScriptVisitor, *args, **kwargs):
        self.scopes = self.scopes.new_child()
        try:
            func(self, *args, **kwargs)
        finally:
            self.scopes = self.scopes.parents

    return _scoped_method


class ScopedVisit:
    __slots__ = ()

    def __get__(self, instance: ScriptVisitor, owner):
        return self if instance is None else partial(scoped(owner.generic_visit), instance)


class ScriptVisitor(NodeVisitor):
    visit_FunctionDef = visit_AsyncFunctionDef = ScopedVisit()
    visit_Lambda = ScopedVisit()
    visit_ClassDef = ScopedVisit()
    visit_While = ScopedVisit()

    def __init__(self, smart_loop_handling: bool = True, track_refs: Collection[TrackedRef] = ()):
        self.smart_loop_handling = smart_loop_handling
        self.scopes = ChainMap()
        self._tracked_refs = set()
        self._mod_name_tracked_map = defaultdict(dict)
        for ref in track_refs:
            self.track_refs_to(ref)

    def track_callable(self, module: str, name: str, cb: Callable):
        self._mod_name_tracked_map[module][name] = cb

    def track_refs_to(self, ref: TrackedRef):
        self._tracked_refs.add(ref)
        self._mod_name_tracked_map[ref.module][ref.name] = ref

    def get_tracked_refs(self) -> TrackedRefMap:
        tracked_refs = defaultdict(set)
        for key, val in self.scopes.items():
            if val in self._tracked_refs:
                tracked_refs[val].add(key)
        tracked_refs.default_factory = None
        return tracked_refs

    # region Imports

    def visit_Import(self, node: Import):
        for module_name, as_name in imp_names(node):
            name_tracked_map = self._mod_name_tracked_map.get(module_name)
            if name_tracked_map:
                log.debug(f'Found module import: {module_name} as {as_name}')
                for name, tracked in name_tracked_map.items():
                    self.scopes[f'{as_name}.{name}'] = tracked

    def visit_ImportFrom(self, node: ImportFrom):
        name_tracked_map = self._mod_name_tracked_map.get(node.module)
        if name_tracked_map:
            for name, as_name in imp_names(node):
                tracked = name_tracked_map.get(name)
                if tracked:
                    log.debug(f'Found tracked import: {node.module}.{name} as {as_name}')
                    self.scopes[as_name] = tracked

    # endregion

    # region Scope Changes

    @scoped
    def visit_For(self, node: For):
        if isinstance(node.target, Name):
            try:
                ele_names = [get_name_repr(ele) for ele in node.iter.elts]  # noqa
            except (AttributeError, TypeError):
                ele_names = ()

            if ele_names and self.smart_loop_handling:
                self._visit_for_smart(node, node.target.id, ele_names)
            else:
                self._visit_for_elements(node, node.target.id, ele_names)
        else:
            self.generic_visit(node)

    visit_AsyncFor = visit_For

    def _visit_for_smart(self, node: For, loop_var: str, ele_names: List[str]):
        log.debug(f'Attempting smart for loop visit for loop_var={loop_var!r} in ele_names={ele_names!r}')
        refs = [ref for ref in (self.scopes.get(name) for name in ele_names) if ref]
        # log.debug(f'  > Found {len(refs)=}, {len(ele_names)=}')

        if len(refs) == len(ele_names) and all(isinstance(ref, AstArgumentParser) for ref in refs):
            parents = set(ref.parent for ref in refs)
            log.debug(f'  > Found parents={len(parents)}')
            if len(parents) == 1:
                parent = next(iter(parents))
                if parent and set(getattr(parent, 'sub_parsers', ())) == set(refs):
                    self.scopes[loop_var] = parent
                    self.generic_visit(node)
                    return

        log.debug('Falling back to generic loop handling')
        self._visit_for_elements(node, loop_var, ele_names)

    def _visit_for_elements(self, node: For, loop_var: str, ele_names: List[str]):
        visited_any = False
        for name in ele_names:
            ref = self.scopes.get(name)
            if ref:
                visited_any = True
                self.scopes[loop_var] = ref
                self.generic_visit(node)

        if not visited_any:
            self.generic_visit(node)

    # endregion

    def resolve_ref(self, name: Union[str, AST, Attribute, Name, expr]):
        if isinstance(name, Attribute) and isinstance(name.value, Call):
            obj = self.visit_Call(name.value)
            attr = name.attr
        else:
            if not isinstance(name, str):
                name = get_name_repr(name)
            try:
                return self.scopes[name]
            except KeyError:
                pass
            try:
                obj_name, attr = name.rsplit('.', 1)
                obj = self.scopes[obj_name]
            except (ValueError, KeyError):
                return None

        try:
            can_call = attr in obj.visit_funcs
        except (AttributeError, TypeError):
            return None
        return getattr(obj, attr) if can_call else None

    def visit_withitem(self, item):
        context_expr = item.context_expr
        func = self.resolve_ref(context_expr)
        if func:
            call = context_expr if isinstance(context_expr, Call) else None
            result = func(item, call, self.get_tracked_refs())
            as_name = item.optional_vars
            if as_name:
                self.scopes[get_name_repr(as_name)] = result

    def visit_Assign(self, node: Assign):
        value = node.value
        if isinstance(value, (Attribute, Name)):  # Assigning an alias to a variable
            ref = self.resolve_ref(value)
            if ref:
                for target in node.targets:
                    self.scopes[get_name_repr(target)] = ref
        elif isinstance(value, Call):
            result = self.visit_Call(value)
            if result is not _NoCall:
                for target in node.targets:
                    self.scopes[get_name_repr(target)] = result  # noq

    def visit_Call(self, node: Call):
        func = self.resolve_ref(node.func)
        if func:
            return func(node, node, self.get_tracked_refs())
        return _NoCall


class TrackedRef:
    __slots__ = ('module', 'name')

    def __init__(self, name: str):
        self.module, self.name = name.rsplit('.', 1)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.module}.{self.name}>'

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.module) ^ hash(self.name)

    def __eq__(self, other: TrackedRef) -> bool:
        return self.name == other.name and self.module == other.module


def imp_names(imp: Import | ImportFrom) -> Iterator[Tuple[str, str]]:
    for alias in imp.names:
        name = alias.name
        as_name = alias.asname or name
        yield name, as_name
