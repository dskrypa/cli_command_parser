from __future__ import annotations

from ast import AST, Call, Attribute, Name, expr, unparse
from typing import Union

__all__ = ['get_name_repr']


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
