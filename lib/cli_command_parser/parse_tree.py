"""
:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union, Optional, Collection, Iterable, Iterator, MutableMapping, Dict, Set, Tuple

from .exceptions import AmbiguousParseTree

if TYPE_CHECKING:
    from .nargs import Nargs
    from .parameters.base import BasePositional
    from .parameters.choice_map import Choice
    from .typing import OptStr, CommandCls

__all__ = ['ParseTree']


class AnyWord:
    __slots__ = ('nargs', 'n', 'remaining')

    nargs: Nargs
    n: int
    remaining: Union[int, float]

    def __init__(self, nargs: Nargs, remaining: Union[int, float, None] = None, n: int = 1):
        self.nargs = nargs
        self.n = n
        if remaining is None:
            self.remaining = float('inf') if nargs.max is None else nargs.max - 1  # -1 since one would be consumed
        else:
            self.remaining = remaining

    def __str__(self) -> str:
        # return '[[AnyWord]]'
        return '*'

    def __repr__(self) -> str:
        return f'AnyWord({self.nargs!r}, remaining={self.remaining}, n={self.n})'

    def __add__(self, other: int) -> AnyWord:
        remaining = self.remaining - other
        if remaining < 0:
            raise ValueError(f'Unable to add {other} to {self!r} - remaining={remaining} is invalid')
        return AnyWord(self.nargs, remaining, self.n + other)


Word = Union[str, AnyWord, None]
Target = Union['BasePositional', 'CommandCls', None]


class NodeLinkMap(MutableMapping[Word, 'PosNode']):
    __slots__ = ('data', 'any_word', 'any_node')

    def __init__(self):
        self.data = {}

    def has_any(self) -> bool:
        try:
            self.any_word
        except AttributeError:
            return False
        else:
            return True

    def __repr__(self) -> str:
        try:
            any_str = f'{self.any_word!r}: {self.any_node!r}'
        except AttributeError:
            any_str = 'None'
        return f'<{self.__class__.__name__}[{any_str}, {self.data!r}]>'

    def __len__(self) -> int:
        try:
            self.any_word
        except AttributeError:
            extra = 0
        else:
            extra = 1
        return len(self.data) + extra

    def __contains__(self, word: Word) -> bool:
        try:
            self.data[word]
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
                self.any_word
            except AttributeError:
                self.any_word = word
                self.any_node = node
            else:
                raise KeyError(f'Choice conflict: {word!r} cannot replace {self.any_word!r}')
        else:
            self.data[word] = node

    def __getitem__(self, word: Word) -> PosNode:
        try:
            return self.data[word]
        except KeyError:
            pass
        try:
            return self.any_node
        except AttributeError:
            pass
        raise KeyError(word)

    def __delitem__(self, word: Word):
        try:
            del self.data[word]
        except KeyError:
            pass
        try:
            any_word = self.any_word
        except AttributeError:
            raise KeyError(word) from None

        if any_word == word:
            del self.any_word
            del self.any_node
        else:
            raise KeyError(word)

    def __iter__(self) -> Iterator[Word]:
        yield from self.data
        try:
            yield self.any_word
        except AttributeError:
            pass

    def items(self) -> Iterator[Tuple[Word, PosNode]]:
        yield from self.data.items()
        try:
            yield self.any_word, self.any_node
        except AttributeError:
            pass


def target_repr(target: Target) -> str:
    try:
        return target.__name__
    except AttributeError:
        return repr(target)


class PosNode:
    __slots__ = ('parent', 'word', 'links', 'target')

    parent: Optional[PosNode]
    word: Word
    links: NodeLinkMap
    target: Target

    def __init__(self, word: Word, target: Target = None, parent: Optional[PosNode] = None):
        self.parent = parent
        self.word = word
        self.links = NodeLinkMap()
        self.target = target

    def __repr__(self) -> str:
        root = self.parent is None
        target = target_repr(self.target)
        return f'<PosNode[{self.path_repr()}: {self.word!r}, links: {len(self.links)}, root: {root}, target={target}]>'

    @property
    def root(self) -> PosNode:
        parent = self.parent
        return parent.root if parent else self

    @property
    def raw_path(self) -> Tuple[Word, ...]:
        word = self.word
        if not word:
            return ()
        try:
            return (*self.parent.raw_path, word)  # noqa
        except AttributeError:
            return (word,)  # noqa

    def path_repr(self) -> str:
        return '({})'.format(', '.join(str(n) if isinstance(n, AnyWord) else repr(n) for n in self.raw_path))

    @property
    def is_terminal(self) -> bool:
        word = self.word
        try:
            return word.n in word.nargs
        except AttributeError:
            return bool(self.target)

    def _set_target(self, target: Target) -> PosNode:
        if not target:
            return self
        elif self.target:
            raise AmbiguousParseTree(self, target)
        else:
            self.target = target
            return self

    def _update_any(self, word: AnyWord, target: Target) -> PosNode:
        try:
            self.links[word]
        except KeyError:
            pass
        else:
            raise AmbiguousParseTree(self, target, word)

        self.links[word] = node = PosNode(word, target, self)
        return node

    def _update(self, word: str, target: Target) -> PosNode:
        links = self.links
        try:
            node = links.data[word]
        except KeyError:
            if links.has_any():
                raise AmbiguousParseTree(self, target, word) from None
            links[word] = node = PosNode(word, target, self)
            return node
        else:
            return node._set_target(target)

    def update(self, word: Word, target: Target) -> PosNode:
        try:
            *parts, last = word.split()
        except AttributeError:  # The choice is None or Any
            if word:
                return self._update_any(word, target)
            else:
                return self._set_target(target)
        else:
            node = self
            for part in parts:
                node = node._update(part, None)
            return node._update(last, target)

    def print_tree(self, indent: int = 0):
        prefix = ' ' * indent
        print(f'{prefix}- <PosNode[{self.word!r}, links: {len(self.links)}, target={self.target!r}]>')
        indent += 2
        for node in self.links.values():
            node.print_tree(indent)


class ParseTree:
    def __init__(self, command: CommandCls):
        self.command = command
        self.root = PosNode(None)
        self._build([self.root], command.__class__.params(command).positionals)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.command!r})[root={self.root!r}]>'

    def _build(self, nodes: Iterable[PosNode], params: Iterable[BasePositional]) -> Set[PosNode]:
        for param in params:
            nodes = self._process_param(nodes, param)

        return nodes

    def _process_param(self, nodes: Iterable[PosNode], param: BasePositional) -> Set[PosNode]:
        # At each step, the number of branches grows
        try:
            choices: Dict[OptStr, Choice] = param.choices  # noqa
        except AttributeError:  # It was not a ChoiceMap param
            pass
        else:
            get_params = self.command.__class__.params

            new_nodes = set()
            for choice in choices.values():
                target = choice.target
                try:
                    params = get_params(target)
                except TypeError:
                    new_nodes.update(node.update(choice.choice, target) for node in nodes)
                else:
                    choice_nodes = {node.update(choice.choice, target) for node in nodes}
                    new_nodes.update(self._build(choice_nodes, params.positionals))

            return new_nodes

        try:
            choices: Collection[str] = param.type.choices  # noqa
        except AttributeError:  # It was not a _ChoicesBase input type
            pass
        else:
            return {node.update(choice, param) for choice in choices for node in nodes}

        # At this point, the param will take any word
        word = AnyWord(param.nargs)
        return {node.update(word, param) for node in nodes}

    def print_tree(self):
        self.root.print_tree()
