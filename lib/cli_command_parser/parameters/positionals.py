"""
Positional Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import ParameterDefinitionError
from ..inputs import normalize_input_type
from ..nargs import Nargs, NargsValue
from ..utils import _NotSet
from .base import BasicActionMixin, BasePositional

if TYPE_CHECKING:
    from ..typing import InputTypeFunc, ChoicesType

__all__ = ['Positional']


class Positional(BasicActionMixin, BasePositional, default_ok=True):
    """
    A parameter that must be provided positionally.

    :param nargs: The number of values that are expected/required for this parameter.  Defaults to 1.  Use a value
      that allows 0 values to have the same effect as making this parameter not required (the ``required`` option
      is not supported for Positional parameters).  Only the last Positional parameter in a given :class:`.Command`
      may allow a variable / unbound number of arguments.  See :class:`.Nargs` for more info.
    :param action: The action to take on individual parsed values.  Actions must be defined as methods in classes
      that extend Parameter, and must be registered via :class:`.parameter_action`.  Defaults to ``store`` when
      ``nargs=1``, and to ``append`` otherwise.  A single value will be stored when ``action='store'``, and a list
      of values will be stored when ``action='append'``.
    :param type: A callable (function, class, etc.) that accepts a single string argument, which should be called
      on every value for this parameter to transform the value.  By default, no transformation is performed, and
      values will be strings.  If not specified, but a type annotation is detected, then that annotation will be
      used as if it was provided here.  When both are present, this argument takes precedence.
    :param default: Only supported when 0 values are allowed by the specified ``nargs``.  If not specified and
      ``action='store'``, then this will default to ``None``; if ``action='append'``, and no values are provided, then
      an empty list will be returned for this Parameter.
    :param choices: A container that holds the specific values that users must pick from.  By default, any value is
      allowed.
    :param kwargs: Additional keyword arguments to pass to :class:`.BasePositional`.
    """

    def __init__(
        self,
        nargs: NargsValue = None,
        action: str = _NotSet,
        type: InputTypeFunc = None,  # noqa
        default: Any = _NotSet,
        *,
        choices: ChoicesType = None,
        **kwargs,
    ):
        if nargs is not None:
            self.nargs = Nargs(nargs)
            if self.nargs == 0:
                cls_name = self.__class__.__name__
                raise ParameterDefinitionError(f'Invalid nargs={self.nargs} - {cls_name} must allow at least 1 value')
        if action is _NotSet:
            action = 'store' if self.nargs == 1 or self.nargs == Nargs('?') else 'append'
        elif action == 'store' and self.nargs.max != 1:
            raise ParameterDefinitionError(f'Invalid action={action!r} for nargs={self.nargs}')
        required = 0 not in self.nargs
        if default is not _NotSet and required:
            raise ParameterDefinitionError(
                f'Invalid default={default!r} - only allowed for Positional parameters when nargs=? or nargs=*'
            )
        kwargs.setdefault('required', required)
        super().__init__(action=action, default=default, **kwargs)
        self.type = normalize_input_type(type, choices)
