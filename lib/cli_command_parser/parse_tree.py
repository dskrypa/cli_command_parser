"""
:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union, Optional, Collection, Generic, TypeVar, Iterable, Callable, overload, Dict, Set

# from .core import get_params
from .exceptions import AmbiguousParseTree

if TYPE_CHECKING:
    from types import MethodType
    from .nargs import Nargs
    from .parameters.base import BasePositional
    from .parameters.choice_map import Choice
    from .typing import OptStr, CommandCls

__all__ = ['ParseTree']

T = TypeVar('T')


class cached_slot_property(Generic[T]):
    __slots__ = ('func', 'name', '__doc__')

    def __init__(self, func: Callable[[MethodType], T]):
        self.func = func
        self.name = None
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name: str):
        self.name = f'_{name}'
        if self.name not in owner.__slots__:
            raise TypeError(f'Missing attr {name!r} in {owner.__name__}.__slots__')

    @overload
    def __get__(self, instance: None, owner) -> cached_slot_property:
        ...

    @overload
    def __get__(self, instance, owner) -> T:
        ...

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return getattr(instance, self.name)
        except AttributeError:
            pass
        value = self.func(instance)
        setattr(instance, self.name, value)
        return value

    def __set__(self, instance, value: T):
        setattr(instance, self.name, value)


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


class PosNode:
    __slots__ = ('parent', 'word', 'links', '_any_link', 'target', '_root', '_path')

    parent: Optional[PosNode]
    word: Word
    links: Dict[OptStr, PosNode]
    _any_link: Optional[PosNode]
    target: Target

    def __init__(self, word: Word, target: Target = None, parent: Optional[PosNode] = None):
        self.parent = parent
        self.word = word
        self.links = {}
        # self.any_link = None
        self.target = target

    def __repr__(self) -> str:
        root = self.parent is None
        return f'<PosNode[{self.word!r}, links: {len(self.links)}, root: {root}, target={self.target!r}]>'

    def __getitem__(self, word: str) -> PosNode:
        try:
            return self.links[word]
        except KeyError:
            pass
        any_link = self.any_link
        if any_link:
            return any_link
        raise KeyError(word)

    @cached_slot_property
    def any_link(self) -> Optional[PosNode]:
        try:
            next_word = self.word + 1
        except (TypeError, ValueError):  # TypeError for None or str, ValueError for no remaining
            return None
        return PosNode(next_word, self.target, self)
        # word = self.word
        # try:
        #     remaining = word.remaining
        # except AttributeError:  # it was a string or None, not AnyWord
        #     return None
        # if not remaining:
        #     return None
        # return PosNode(AnyWord(word.nargs, remaining - 1, word.n + 1), self.target, self)

    @cached_slot_property
    def root(self) -> PosNode:
        parent = self.parent
        return parent.root if parent else self

    # @cached_slot_property
    # def path(self) -> tuple[str, ...]:
    #     parts = []
    #     node = self
    #     while node:
    #         parts.append(node.word)
    #         node = node.parent
    #     return tuple(parts[:-1][::-1])

    @cached_slot_property
    def path(self) -> tuple[str, ...]:
        word = self.word
        if not word:
            return ()
        word = str(word)
        try:
            return (*self.parent.path, word)  # noqa
        except AttributeError:
            return (word,)  # noqa

    @property
    def is_terminal(self) -> bool:
        word = self.word
        try:
            return word.n in word.nargs
        except AttributeError:
            return bool(self.target)

    def _update(self, word: Word, target: Target) -> PosNode:
        if word:
            any_link, own_word = self.any_link, self.word
            if any_link and self.is_terminal:
                raise AmbiguousParseTree(self, word, target)
            elif isinstance(word, AnyWord):
                if any_link or self.links:
                    raise AmbiguousParseTree(self, word, target)
                else:
                    self.any_link = node = PosNode(word, target, self)  # noqa
                    return node
            else:
                try:
                    node = self.links[word]
                except KeyError:
                    self.links[word] = node = PosNode(word, target, self)
                    return node
                else:
                    return node._update(None, target)
        # Below this point, word is None
        elif not target:
            return self
        elif self.target:
            raise AmbiguousParseTree(self, word, target)
        else:
            self.target = target
            return self

    def update(self, word: Word, target: Target) -> PosNode:
        try:
            *parts, last = word.split()
        except AttributeError:  # The choice is None or Any
            return self._update(word, target)
        else:
            node = self
            for part in parts:
                node = node.update(part, None)
            return node._update(last, target)

    def print_tree(self, indent: int = 0):
        prefix = ' ' * indent
        print(f'{prefix}- <PosNode[{self.word!r}, links: {len(self.links)}, target={self.target!r}]>')
        indent += 2
        for node in self.links.values():
            node.print_tree(indent)

        try:
            self.any_link.print_tree(indent)
        except AttributeError:  # any_link is None
            pass


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
