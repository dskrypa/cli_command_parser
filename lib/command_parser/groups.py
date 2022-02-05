"""
:author: Doug Skrypa
"""

import logging
from threading import Lock
from typing import TYPE_CHECKING, Any, Optional, Union, Iterator

from .exceptions import ParameterDefinitionError, UsageError

if TYPE_CHECKING:
    from .commands import CommandType
    from .parameters import Parameter
    from .utils import Args

__all__ = ['ParameterGroup']
log = logging.getLogger(__name__)


class ParameterGroup:
    """
    A group of parameters.

    Group nesting is not implemented due to the complexity and potential confusion that it would add for cases where
    differing mutual exclusivity/dependency rules would need to be resolved.  In theory, though, it should be possible.
    """

    _lock = Lock()
    _active: Optional['ParameterGroup'] = None

    def __init__(
        self,
        name: str = None,
        *,
        description: str = None,
        mutually_exclusive: Union[bool, Any] = False,
        mutually_dependent: Union[bool, Any] = False,
    ):
        self.name = name
        self.description = description
        self.parameters: list['Parameter'] = []
        if mutually_dependent and mutually_exclusive:
            name = self.name or 'Options'
            raise ParameterDefinitionError(f'group={name!r} cannot be both mutually_exclusive and mutually_dependent')
        self.mutually_exclusive = mutually_exclusive
        self.mutually_dependent = mutually_dependent

    def register(self, param: 'Parameter'):
        self.parameters.append(param)
        param.group = self

    def __set_name__(self, owner: 'CommandType', name: str):
        if self.name is None:
            self.name = name

    def __repr__(self) -> str:
        exclusive, dependent = self.mutually_exclusive, self.mutually_dependent
        members = len(self.parameters)
        return f'<{self.__class__.__name__}[{self.name!r}, {members=}, m.{exclusive=!s}, m.{dependent=!s}]>'

    def __enter__(self) -> 'ParameterGroup':
        self._lock.acquire()
        self.__class__._active = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__class__._active = None
        self._lock.release()
        return None

    def __iter__(self) -> Iterator['Parameter']:
        yield from self.parameters

    def _categorize_params(self, args: 'Args') -> tuple[list['Parameter'], list['Parameter']]:
        provided = []
        missing = []
        for param in self.parameters:
            if args.num_provided(param):
                provided.append(param)
            else:
                missing.append(param)

        return provided, missing

    def check_conflicts(self, args: 'Args'):
        # log.debug(f'{self}: Checking group conflicts in {args=}')
        if not (self.mutually_dependent or self.mutually_exclusive):
            return

        provided, missing = self._categorize_params(args)
        # log.debug(f'{provided=}, {missing=}')
        # log.debug(f'provided={len(provided)}, missing={len(missing)}')
        if self.mutually_dependent and provided and missing:
            p_str = ', '.join(p.format_usage(full=True, delim='/') for p in provided)
            m_str = ', '.join(p.format_usage(full=True, delim='/') for p in missing)
            be = 'is' if len(provided) == 1 else 'are'
            raise UsageError(f'When {p_str} {be} provided, then the following must also be provided: {m_str}')
        elif self.mutually_exclusive and not 0 <= len(provided) < 2:
            p_str = ', '.join(p.format_usage(full=True, delim='/') for p in provided)
            raise UsageError(f'The following arguments are mutually exclusive - only one is allowed: {p_str}')
