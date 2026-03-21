"""
:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Collection, Iterable, Iterator, MutableMapping, Type, TypeAlias

from .core import get_params
from .exceptions import AmbiguousParseTree
from .utils import _parse_tree_target_repr

if TYPE_CHECKING:
    from .commands import Command
    from .core import CommandMeta
    from .nargs import Nargs
    from .parameters.base import BasePositional
    from .parameters.choice_map import Choice, ChoiceMap
    from .typing import OptStr

    CommandCls: TypeAlias = Type[Command] | CommandMeta
    Target: TypeAlias = BasePositional | CommandCls | None

__all__ = ['PosNode']


class AnyWord:
    __slots__ = ('nargs', 'n', 'remaining')

    nargs: Nargs
    n: int
    remaining: int | float

    def __init__(self, nargs: Nargs, remaining: int | float | None = None, n: int = 1):
        self.nargs = nargs
        self.n = n
        if remaining is None:
            self.remaining = nargs.upper_bound - 1  # -1 since one would be consumed
        else:
            self.remaining = remaining

    def __repr__(self) -> str:
        return f'AnyWord({self.nargs!r}, remaining={self.remaining}, n={self.n})'

    def __add__(self, other: int) -> AnyWord:
        remaining = self.remaining - other
        if remaining < 0:
            raise ValueError(f'Unable to add {other} to {self!r} - {remaining=} is invalid')
        return AnyWord(self.nargs, remaining, self.n + other)

    def __eq__(self, other) -> bool:
        try:
            return self.nargs == other.nargs and self.remaining == other.remaining and self.n == other.n
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.nargs) ^ hash(self.remaining) ^ hash(self.n)


Word = str | AnyWord | None


class PosNode(MutableMapping[Word, 'PosNode']):
    __slots__ = ('links', 'param', 'parent', 'target', 'word', '_any_word', '_any_node')

    links: dict[Word, PosNode]
    parent: PosNode | None
    word: Word
    _any_word: AnyWord

    def __init__(self, word: Word, param: BasePositional | None, target: Target = None, parent: PosNode | None = None):
        self.links = {}
        self.param: BasePositional | None = param
        self.parent = parent
        self.target: Target = target
        self.word = word
        if parent is not None:
            parent[word] = self

    def link_params(self, recursive: bool = False) -> set[BasePositional]:
        return set(self._link_params(recursive))

    def _link_params(self, recursive: bool = False) -> Iterator[BasePositional]:
        for node in self.values():
            if node.param is not None:  # Technically, only the root node would actually have a param that is None
                yield node.param

        if recursive:
            for node in self.values():
                yield from node._link_params(_has_upper_bound(node))

    # region AnyWord Methods

    @property
    def any_word(self) -> AnyWord:
        try:
            return self._any_word  # setitem was called with an AnyWord object
        except AttributeError:
            try:
                # child word will be guaranteed to be an AnyWord if child creation succeeds
                return self._create_child().word  # type: ignore[return-value]
            except (ValueError, TypeError):
                pass
            raise

    @property
    def any_node(self) -> PosNode:
        try:
            return self._any_node  # setitem was called with an AnyWord object
        except AttributeError:
            try:
                return self._create_child()
            except (ValueError, TypeError):
                pass
            raise

    def has_any(self) -> bool:
        try:
            self.any_word  # noqa
        except AttributeError:
            return False

        return True

    def _create_child(self) -> PosNode:
        if not isinstance(self.word, AnyWord):
            raise TypeError(f'Unable to create child for node with word={self.word!r}')

        word = self.word + 1  # Will raise ValueError if self.word has remaining < 1
        return PosNode(word, self.param, self.target, self)

    # endregion

    # region Introspection

    def _raw_path(self) -> Iterator[Word]:
        if self.parent:
            yield from self.parent._raw_path()
        if self.word:
            yield self.word

    def path_repr(self, for_parent: bool = False) -> str:
        if for_parent:
            if self.parent is not None:
                raw_path = self.parent._raw_path()
            else:
                return '()'
        else:
            raw_path = self._raw_path()
        return '({})'.format(', '.join(str(n) if isinstance(n, AnyWord) else repr(n) for n in raw_path))

    # endregion

    # region Dunder Methods

    def __repr__(self) -> str:
        if self.param == self.target:
            pt_str = f'param=target={_parse_tree_target_repr(self.target)}'
        else:
            pt_str = f'param={self.param}, target={_parse_tree_target_repr(self.target)}'
        return f'<PosNode[{self.path_repr()}: {self.word!r}, links: {len(self)}, {pt_str}]>'

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self.parent) ^ hash(self.word) ^ hash(self.param) ^ hash(self.target)

    def __eq__(self, other) -> bool:
        if not isinstance(other, PosNode):
            return False

        return (
            self.parent == other.parent
            and self.param == other.param
            and self.word == other.word
            and self.target == other.target
            and self.links == other.links
        )

    def __bool__(self) -> bool:
        if self.links:
            return True
        return self.has_any()

    def __len__(self) -> int:
        return len(self.links) + self.has_any()

    def __contains__(self, word: Word) -> bool:  # type: ignore[override]
        try:
            self.links[word]
        except KeyError:
            pass
        else:
            return True

        try:
            return self.any_word == word
        except AttributeError:
            return False

    def __setitem__(self, word: Word, node: PosNode):
        if isinstance(word, AnyWord):
            try:
                self._any_word
            except AttributeError:
                try:
                    next_word = self.word + 1  # type: ignore[operator]
                except (TypeError, ValueError):  # not an AnyWord or the AnyWord is full
                    pass
                else:
                    if word != next_word or node.parent is not self or node.param is not self.param:
                        raise KeyError(f'Choice conflict: {word!r}=>{node} cannot replace {next_word!r}')

                self._any_word = word
                self._any_node = node
                return

            raise KeyError(f'Choice conflict: {word!r}=>{node} cannot replace {self._any_word!r}=>{self._any_node}')
        else:
            self.links[word] = node

    def __getitem__(self, word: Word) -> PosNode:
        try:
            return self.links[word]
        except KeyError:
            pass
        try:
            return self.any_node
        except AttributeError:
            pass
        raise KeyError(word)

    def __delitem__(self, word: Word):
        try:
            del self.links[word]
        except KeyError:
            pass
        else:
            return
        try:
            any_word = self._any_word
        except AttributeError:
            raise KeyError(word) from None

        if any_word == word:
            del self._any_word
            del self._any_node
        else:
            raise KeyError(word)

    def __iter__(self) -> Iterator[Word]:
        yield from self.links
        try:
            yield self.any_word
        except AttributeError:
            pass

    # endregion

    # region Build Tree

    @classmethod
    def build_tree(cls, command: CommandCls) -> PosNode:
        root = cls(None, None, target=command)
        _process_params(command, [root], get_params(command).all_positionals)
        return root

    def update_node(self, word: Word, param: BasePositional, target: Target) -> PosNode:
        match word:
            case str():
                *parts, last = word.split()
                node = self
                for part in parts:
                    node = node._update(part, param, None)
                return node._update(last, param, target)
            case AnyWord():
                return self._update_any(word, param, target)
            case _:  # Assume None
                return self._set_target(target)

    def _set_target(self, target: Target) -> PosNode:
        if not target:
            return self
        elif self.target and self.word:
            raise AmbiguousParseTree(self, target)
        else:
            self.target = target
            return self

    def _update(self, word: str, param: BasePositional, target: Target) -> PosNode:
        links = self.links
        try:
            node = links[word]
        except KeyError:
            if self.has_any():
                raise AmbiguousParseTree(self, target, word) from None
            return PosNode(word, param, target, self)
        else:
            return node._set_target(target)

    def _update_any(self, word: AnyWord, param: BasePositional, target: Target) -> PosNode:
        try:
            self[word]
        except KeyError:
            pass
        else:
            raise AmbiguousParseTree(self, target, word)

        node = PosNode(word, param, target, self)
        # TODO: This needs to be converted to be lazy instead
        if word.nargs.has_upper_bound:
            while True:
                try:
                    node = node._create_child()
                except ValueError:
                    break

        return node

    # endregion

    def print_tree(self, indent: int = 0, recursive: bool = True):
        prefix = ' ' * indent
        print(f'{prefix}- <PosNode[{self.word!r}, links: {len(self)}, target={_parse_tree_target_repr(self.target)}]>')
        if not recursive:
            return
        indent += 2
        for node in self.values():
            node.print_tree(indent, _has_upper_bound(node))


def _has_upper_bound(node) -> bool:
    try:
        return node.word.nargs.has_upper_bound
    except AttributeError:
        return True


def _process_params(
    command: CommandCls, nodes: Iterable[PosNode], params: Iterable[BasePositional]
) -> Iterable[PosNode]:
    for param in params:
        nodes = _process_param(command, nodes, param)

    return nodes


def _process_param(command: CommandCls, nodes: Iterable[PosNode], param: BasePositional | ChoiceMap) -> set[PosNode]:
    # At each step, the number of branches grows
    try:
        choices: dict[OptStr, Choice[CommandCls]] = param.choices  # type: ignore[union-attr]
    except AttributeError:  # It was not a ChoiceMap param
        pass
    else:
        new_nodes: set[PosNode] = set()
        for choice in choices.values():
            target = choice.target
            try:
                params = get_params(target)
            except TypeError:
                new_nodes.update(node.update_node(choice.choice, param, target) for node in nodes)
            else:
                choice_nodes = {node.update_node(choice.choice, param, target) for node in nodes}
                new_nodes.update(_process_params(target, choice_nodes, params.all_positionals))

        return new_nodes

    try:
        type_choices: Collection[str] = param.type.choices  # type: ignore[union-attr]
    except AttributeError:  # It was not a _ChoicesBase input type
        pass
    else:
        return {node.update_node(choice, param, param) for choice in type_choices for node in nodes}

    # At this point, the param will take any word
    word = AnyWord(param.nargs)
    return {node.update_node(word, param, param) for node in nodes}
