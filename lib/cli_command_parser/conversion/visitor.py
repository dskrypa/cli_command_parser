from __future__ import annotations

import logging
import re
from ast import AST, Assign, Attribute, Call, For, Import, ImportFrom, Name, NodeVisitor, withitem
from collections import ChainMap, defaultdict
from enum import Enum
from functools import partial, wraps
from typing import TYPE_CHECKING, Callable, Collection, Iterator, Literal, Union, overload

from .argparse_ast import AstArgumentParser, AstCallable, VisitFunc
from .utils import get_name_repr

if TYPE_CHECKING:
    TrackedRefMap = dict['TrackedRef', set[str]]
    NameTrackedMap = dict[str, Union[Callable, 'TrackedRef']]
    TrackedValue = Union['TrackedRef', VisitFunc, AstCallable]
    RefName = str | AST

__all__ = ['ScriptVisitor', 'TrackedRef']
log = logging.getLogger(__name__)


class _NoCallType(Enum):
    """Provides the sentinel value for _NoCall in a way that is fully compatible with type checkers."""

    _NoCall = '_NoCall'

    def __str__(self) -> str:
        return self.name


_NoCall = _NoCallType._NoCall


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
    scopes: ChainMap[str, TrackedValue]

    visit_FunctionDef = visit_AsyncFunctionDef = ScopedVisit()
    visit_Lambda = ScopedVisit()
    visit_ClassDef = ScopedVisit()
    visit_While = ScopedVisit()

    def __init__(self, smart_loop_handling: bool = True, track_refs: Collection[TrackedRef] = ()):
        self.smart_loop_handling = smart_loop_handling
        self.scopes = ChainMap()  # ChainMap that tracks the var/class/func/etc names available in a given scope
        self._tracked_refs: set[TrackedRef] = set()  # References that are tracked, but not meant to be called
        self._mod_name_tracked_map: dict[str, NameTrackedMap] = defaultdict(dict)  # All tracked items by source module
        for ref in track_refs:
            self.track_refs_to(ref)

    def track_callable(self, module: str, name: str, cb: Callable):
        self._mod_name_tracked_map[module][name] = cb

    def track_refs_to(self, ref: TrackedRef):
        """Register a reference that should be tracked."""
        self._tracked_refs.add(ref)
        self._mod_name_tracked_map[ref.module][ref.name] = ref

    def get_tracked_refs(self) -> TrackedRefMap:
        tracked_refs = defaultdict(set)
        for key, val in self.scopes.items():
            if val in self._tracked_refs:
                tracked_refs[val].add(key)

        tracked_refs.default_factory = None  # disable creation of new sets on future key misses
        return tracked_refs  # type: ignore[return-value]

    # region Imports

    def visit_Import(self, node: Import):
        """
        Processes a ``import some_module`` or ``import some_module as other_name`` statement.

        :param node: The AST object representing the import statement.
        """
        for module_name, as_name in imp_names(node):
            if name_tracked_map := self._mod_name_tracked_map.get(module_name):
                # One or more items in the specified module were registered to be tracked
                log.debug(f'Found module import: {module_name} as {as_name}')
                for name, tracked in name_tracked_map.items():
                    self.scopes[f'{as_name}.{name}'] = tracked

    def visit_ImportFrom(self, node: ImportFrom):
        """
        Processes a ``from module import names`` statement.  If the module name matches one from which members were
        registered to be tracked, then the imported names (and any ``as`` aliases) are processed.  Members with
        canonical names that match an item that was registered to be tracked are added to the current scope / variable
        namespace.

        Relative module imports are handled fuzzily - no attempt is made to determine the fully qualified module name
        for the source file or to resolve what the relative import's fully qualified module name would be.  This may
        result in incorrect items being tracked if the name matched a tracked name in the matched tracked module.
        """
        # `from foo.bar import x,y,z` -> level = 0 - absolute import, so node.module = 'foo.bar'
        # `from . import x,y,z` -> level = 1 - relative import with no module, so node.module = None
        # `from ..foo.bar import x,y,z` -> level 2 - relative import with a module, so node.module = 'foo.bar'
        if not node.module:
            # Only relative imports (of any level) with no specific module name result in node.module = None
            return  # Tracking relative imports with no explicit module name is not supported

        if level := node.level:
            # It's a relative import - attempt to fuzzily match tracked modules with the same depth that end with the
            # specified module name
            matches = re.compile(r'[^.]+\.' * level + re.escape(node.module) + '$').search
            for module, name_tracked_map in self._mod_name_tracked_map.items():
                if matches(module):
                    log.debug(f'Found fuzzy relative name match for {"." * level + node.module!r} to {module=}')
                    self._maybe_track_import_from(node, name_tracked_map)
        elif name_tracked_map := self._mod_name_tracked_map.get(node.module):  # type: ignore[assignment]
            # It's an absolute import and the module name matches an item that is being tracked
            self._maybe_track_import_from(node, name_tracked_map)

    def _maybe_track_import_from(self, node: ImportFrom, name_tracked_map: NameTrackedMap):
        """
        If any of the items imported from the specified module match an item that is being tracked, add the local name
        that is being used for it (the ``as other_name`` value, if specified, otherwise the original name) to the
        current scope.
        """
        for name, as_name in imp_names(node):
            if tracked := name_tracked_map.get(name):
                log.debug(f'Found tracked import: {node.module}.{name} as {as_name}')
                self.scopes[as_name] = tracked

    # endregion

    # region Scope Changes

    @scoped
    def visit_For(self, node: For):
        """Visit a *for* loop."""
        # Given the loop, `for x in y:`, `For.target` -> `x` (the loop variable), and `For.iter` -> `y` (the iterable)
        if isinstance(node.target, Name):
            # `For.target` -> the loop variable(s); if the target is a Name, then it is a single variable.
            # For loops with multiple loop variables result in the target being a tuple of Names.
            try:
                # When the iterable is an in-line collection literal such as a tuple, `node.iter` will be the AST
                # object representing that collection literal. The `elts` attr of Tuple/List/Set contains its elements.
                ele_names = [get_name_repr(ele) for ele in node.iter.elts]  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                ele_names = []

            if ele_names and self.smart_loop_handling:
                self._visit_for_smart(node, node.target.id, ele_names)
            else:
                self._visit_for_elements(node, node.target.id, ele_names)
        else:
            self.generic_visit(node)

    visit_AsyncFor = visit_For

    def _visit_for_smart(self, node: For, loop_var: str, ele_names: list[str]):
        """
        Processes *for* loops that iterate over tracked parser objects for the purpose of registering common
        arguments, etc.  If not all of the identified elements are parsers, then this method falls back to the
        generic :meth:`._visit_for_elements` handler instead.

        :param node: An AST node representing a *for* loop over an in-line tuple/list/set literal.
        :param loop_var: Given ``for x in y:``, ``x``.
        :param ele_names: The names of the items in the tuple/list/set literal.
        """
        log.debug(f'Attempting smart for loop visit for {loop_var=} in {ele_names=}')
        refs: list[AstArgumentParser] = [
            ref  # type: ignore[misc]  # mypy doesn't seem to recognize the isinstance part of the condition
            for name in ele_names
            if (ref := self.scopes.get(name)) and isinstance(ref, AstArgumentParser)
        ]
        # log.debug(f'  > Found {len(refs)=}, {len(ele_names)=}')

        if len(refs) == len(ele_names):  # ele_names is confirmed to be non-empty before this method is called
            # All elements are AstArgumentParser or SubParser (or subclasses thereof) objects
            parents = set(ref.parent for ref in refs)
            log.debug(f'  > Found parents={len(parents)}')
            if len(parents) == 1:
                # They all have the same parent parser or script
                parent = next(iter(parents))
                if parent and set(getattr(parent, 'sub_parsers', ())) == set(refs):
                    # They are all subparsers with the same parent parser, and the parent parser does not have any
                    # other subparsers that are not in scope for this loop.
                    # Pretend the parent is the target - ignore the subparsers when evaluating the loop, and add the
                    # common items to the parent parser.
                    self.scopes[loop_var] = parent  # type: ignore[assignment]
                    self.generic_visit(node)
                    return

        log.debug('Falling back to generic loop handling')
        self._visit_for_elements(node, loop_var, ele_names)

    def _visit_for_elements(self, node: For, loop_var: str, ele_names: list[str]):
        visited_any = False
        for name in ele_names:
            if ref := self.scopes.get(name):
                visited_any = True
                self.scopes[loop_var] = ref
                self.generic_visit(node)

        if not visited_any:
            self.generic_visit(node)

    # endregion

    # region Resolve Tracked References

    @overload
    def resolve_ref(self, name: RefName, only_visitable: Literal[False] = False) -> VisitFunc | AstCallable | None: ...

    @overload
    def resolve_ref(self, name: RefName, only_visitable: Literal[True]) -> VisitFunc | None: ...

    def resolve_ref(self, name: RefName, only_visitable: bool = False) -> VisitFunc | AstCallable | None:
        """
        Resolve the given reference to a tracked item in the current scope.

        :param name: The name of a reference or an AST node that may contain the name of a reference
        :param only_visitable: If True, then only return visit functions or None, otherwise include AstCallable objects
        :return: The resolved reference
        """
        obj, attr = self._resolve(name)
        match obj:
            case AstCallable():
                if attr:
                    return getattr(obj, attr) if attr in obj.visit_funcs else None
                return None if only_visitable else obj
            case None | TrackedRef():
                return None
            case _:
                return obj if attr is None else None

    def _resolve(self, name: RefName) -> tuple[TrackedValue | None, str | None]:
        """Resolves the given reference, but does not handle final attr lookup or type checking."""
        obj: TrackedRef | VisitFunc | AstCallable | None | _NoCallType
        if isinstance(name, Attribute) and isinstance(name.value, Call):
            if (obj := self.visit_Call(name.value)) is _NoCall:
                return None, None
            return obj, name.attr

        if not isinstance(name, str):
            name = get_name_repr(name)

        if obj := self.scopes.get(name):
            return obj, None

        try:
            obj_name, attr = name.rsplit('.', 1)
            obj = self.scopes[obj_name]
        except (ValueError, KeyError):
            return None, None

        return obj, attr

    # endregion

    def visit_withitem(self, item: withitem):
        """
        Visit a single ``withitem`` / context expression within a ``with ...:`` statement that may include one or more
        ``withitem``s / content expressions.
        """
        context_expr = item.context_expr
        if func := self.resolve_ref(context_expr, True):
            # Found a ``with foo(...):`` statement where *foo* is being tracked
            call = context_expr if isinstance(context_expr, Call) else None
            result = func(item, call, self.get_tracked_refs())
            if as_name := item.optional_vars:
                self.scopes[get_name_repr(as_name)] = result

    def visit_Assign(self, node: Assign):
        """
        Visit an assignment statement where one or more variables (stored in ``Assign.targets``) are being assigned one
        or more values (stored in ``Assign.value``).
        """
        match node.value:
            case Attribute() | Name():
                # Assigning an alias to a variable; e.g., `foo = bar` or `foo = bar.baz`
                if ref := self.resolve_ref(node.value):
                    # The value was singular and referenced something being tracked
                    for target in node.targets:
                        self.scopes[get_name_repr(target)] = ref
                # Not handled here: cases like `a = (1, 2); x, y = a` or `x, y = a, b`
            case Call():
                # Storing the result of a function/similar call; e.g., `foo = bar()` or `foo = bar.baz()`
                if (result := self.visit_Call(node.value)) is not _NoCall:
                    for target in node.targets:
                        self.scopes[get_name_repr(target)] = result

    def visit_Call(self, node: Call) -> AstCallable | _NoCallType:
        if func := self.resolve_ref(node.func, True):
            return func(node, node, self.get_tracked_refs())
        return _NoCall


class TrackedRef:
    """
    Represents any class/function/object/variable/etc. that may be imported from a specific module with a specific
    name in that module.  Used to track references to that item.
    """

    __slots__ = ('module', 'name')

    def __init__(self, name: str):
        self.module, self.name = name.rsplit('.', 1)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}: {self.module}.{self.name}>'

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.module) ^ hash(self.name)

    def __eq__(self, other) -> bool:
        return self.__class__ == other.__class__ and self.name == other.name and self.module == other.module


def imp_names(imp: Import | ImportFrom) -> Iterator[tuple[str, str]]:
    for alias in imp.names:
        name = alias.name
        as_name = alias.asname or name
        yield name, as_name
