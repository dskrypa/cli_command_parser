"""
Positional Parameters

:author: Doug Skrypa
"""

from typing import Any

from ..exceptions import ParameterDefinitionError
from ..inputs import InputTypeFunc, normalize_input_type
from ..nargs import Nargs, NargsValue
from ..utils import _NotSet
from .base import BasicActionMixin, BasePositional

__all__ = ['Positional']


class Positional(BasicActionMixin, BasePositional):
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
    :param default: Only supported when ``action='store'`` and 0 values are allowed by the specified ``nargs``.
      Defaults to ``None`` under those conditions.
    :param kwargs: Additional keyword arguments to pass to :class:`.BasePositional`.
    """

    def __init__(
        self,
        nargs: NargsValue = None,
        action: str = _NotSet,
        type: InputTypeFunc = None,  # noqa
        default: Any = _NotSet,
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
        if default is not _NotSet and (action != 'store' or 0 not in self.nargs):
            raise ParameterDefinitionError(
                f'Invalid default={default!r} - only allowed for Positional parameters when nargs=?'
            )
        super().__init__(action=action, **kwargs)
        self.type = normalize_input_type(type, self.choices)
        if action == 'append':
            self._init_value_factory = list
        if 0 in self.nargs:
            self.required = False
            if action == 'store':
                self.default = None if default is _NotSet else default
