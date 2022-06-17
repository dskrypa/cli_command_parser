from typing import TYPE_CHECKING, Union, TypeVar, List

if TYPE_CHECKING:
    from .base import Parameter
    from .groups import ParamGroup

__all__ = ['Param', 'ParamList', 'ParamOrGroup']

Param = TypeVar('Param', bound='Parameter')
ParamList = List[Param]
ParamOrGroup = Union[Param, 'ParamGroup']
