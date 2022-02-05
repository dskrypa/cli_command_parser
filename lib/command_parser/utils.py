"""
:author: Doug Skrypa
"""

import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Union, Sequence, Optional, Type
from string import whitespace, printable

from .exceptions import ParameterDefinitionError

if TYPE_CHECKING:
    from .parameters import Parameter

Bool = Union[bool, Any]

_NotSet = object()


class Args:
    def __init__(self, args: Optional[Sequence[str]]):
        self.raw = sys.argv[1:] if args is None else args
        self.remaining = self.raw
        self._parsed = {}
        self._provided = defaultdict(int)

    def __repr__(self) -> str:
        # return f'<{self.__class__.__name__}[raw={self.raw}]>'
        provided = dict(self._provided)
        return f'<{self.__class__.__name__}[parsed={self._parsed}, remaining={self.remaining}, {provided=}]>'

    def record_action(self, param: 'Parameter', val_count: int = 1):
        self._provided[param.name] += val_count

    def num_provided(self, param: 'Parameter') -> int:
        return self._provided[param.name]

    def __getitem__(self, param: 'Parameter'):
        try:
            return self._parsed[param.name]
        except KeyError:
            self._parsed[param.name] = value = param._init_value_factory()
            return value

    def __setitem__(self, param: 'Parameter', value):
        self._parsed[param.name] = value


def validate_positional(
    param_cls: str, value: str, prefix: str = 'name', exc: Type[Exception] = ParameterDefinitionError
):
    if not value or value.startswith('-'):
        raise exc(f"Invalid {param_cls} {prefix}={value!r} - may not be empty or start with '-'")
    elif bad := {c for c in value if (c in whitespace and c != ' ') or c not in printable}:
        raise exc(f'Invalid {param_cls} {prefix}={value!r} - invalid characters: {bad}')
