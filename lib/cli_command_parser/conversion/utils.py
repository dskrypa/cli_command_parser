from __future__ import annotations

from ast import AST, Attribute, Call, Dict, List, Name, Set, Tuple, expr, unparse
from typing import Iterator

__all__ = ['get_name_repr', 'iter_module_parents', 'collection_contents']


def get_name_repr(node: AST | expr) -> str:
    if isinstance(node, Call):
        # Call nodes include the arguments passed to the func/callable being called - we want the name of the callable
        node = node.func

    match node:
        case Name():
            # Name = a variable
            return node.id  # the name of the variable
        case Attribute():
            # `foo.bar.baz` -> Attribute(value=Attribute(value=Name(id='foo'), attr='bar'), attr='baz')
            return f'{get_name_repr(node.value)}.{node.attr}'
        case AST():
            return unparse(node)  # returns the original source code for the provided AST object
        case _:
            raise TypeError(f'Only AST nodes are supported - found {type(node).__name__}')


def iter_module_parents(module: str) -> Iterator[str]:
    """
    Given a nested module name, yields parent package names in ascending order.

    I.e., given ``foo.bar.baz``, this function will yield ``foo.bar`` and then ``foo``.
    """
    while True:
        parent = module.rsplit('.', 1)[0]
        if parent == module:
            break
        yield parent
        module = parent


def collection_contents(node: AST) -> list[str]:
    """
    Returns a list of individually unparsed (original source code strings) elements that would be processed when
    iterating over the specified node.

    Silently ignores any dictionaries that were expanded within a dict literal.

    :param node: An AST node representing a dict/list/set/tuple literal.
    :return: List of elements as strings of source code.
    """
    match node:
        case Dict():
            # Dict expansion like `{'a': 1, **some_mapping}` results in key=None for each expanded mapping
            return [unparse(key) for key in node.keys if key is not None]
        case List() | Set() | Tuple():
            return [unparse(ele) for ele in node.elts]
        case _:
            raise TypeError(f'Unexpected AST node type={node.__class__.__name__}')
