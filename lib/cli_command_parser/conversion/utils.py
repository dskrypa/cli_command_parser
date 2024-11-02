from __future__ import annotations

from ast import AST, Attribute, Call, Dict, List, Name, Set, Tuple, expr, unparse
from typing import Iterator, List as _List, Union

__all__ = ['get_name_repr', 'iter_module_parents', 'collection_contents']


def get_name_repr(node: Union[AST, expr]) -> str:
    if isinstance(node, Call):
        node = node.func

    if isinstance(node, Name):
        return node.id
    elif isinstance(node, Attribute):
        return f'{get_name_repr(node.value)}.{node.attr}'  # noqa
    elif isinstance(node, AST):
        return unparse(node)
    else:
        raise TypeError(f'Only AST nodes are supported - found {node.__class__.__name__}')


def iter_module_parents(module: str) -> Iterator[str]:
    while True:
        parent = module.rsplit('.', 1)[0]
        if parent == module:
            break
        yield parent
        module = parent


def collection_contents(node: AST) -> _List[str]:
    if isinstance(node, Dict):
        return [unparse(key) for key in node.keys]  # noqa
    elif isinstance(node, (List, Set, Tuple)):
        return [unparse(ele) for ele in node.elts]  # noqa
    else:
        raise TypeError(f'Unexpected AST node type={node.__class__.__name__}')
