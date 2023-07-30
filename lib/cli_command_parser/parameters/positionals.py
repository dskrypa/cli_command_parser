"""
Positional Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from ..exceptions import ParameterDefinitionError
from ..inputs import normalize_input_type
from ..nargs import Nargs, NargsValue
from ..utils import _NotSet
from .actions import Store, Append
from .base import BasePositional, AllowLeadingDashProperty

if TYPE_CHECKING:
    from ..typing import InputTypeFunc, ChoicesType, LeadingDash, DefaultFunc

__all__ = ['Positional']


class Positional(BasePositional, default_ok=True, actions=(Store, Append)):
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
    :param allow_leading_dash: Whether string values may begin with a dash (``-``).  By default, if a value begins with
      a dash, it is only accepted if it appears to be a negative numeric value.  Use ``True`` / ``always`` /
      ``AllowLeadingDash.ALWAYS`` to allow any value that begins with a dash (as long as it is not an option string for
      an Option/Flag/etc).  To reject all values beginning with a dash, including numbers, use ``False`` / ``never`` /
      ``AllowLeadingDash.NEVER``.
    :param kwargs: Additional keyword arguments to pass to :class:`.BasePositional`.
    """

    allow_leading_dash = AllowLeadingDashProperty()

    def __init__(
        self,
        nargs: NargsValue = None,
        action: Literal['store', 'append'] = None,
        type: InputTypeFunc = None,  # noqa
        default: Any = _NotSet,
        *,
        default_cb: DefaultFunc = None,
        choices: ChoicesType = None,
        allow_leading_dash: LeadingDash = None,
        **kwargs,
    ):
        if nargs_provided := nargs is not None:
            self.nargs = nargs = Nargs(nargs)
            if nargs == 0:
                raise ParameterDefinitionError(
                    f'Invalid {nargs=} - {self.__class__.__name__} must allow at least 1 value'
                )
        else:
            self.nargs = nargs = Nargs(1)

        if not action:
            if nargs_provided:
                action = 'store' if nargs == 1 or nargs == Nargs('?') else 'append'
            else:
                action = 'store'
        elif nargs_provided and action == 'store' and nargs.max != 1:
            raise ParameterDefinitionError(f'Invalid {action=} for {nargs=}')

        if (required := 0 not in nargs) and (default is not _NotSet or default_cb is not None):
            raise ParameterDefinitionError(
                f'Invalid {default=} or {default_cb=} - only allowed for Positional parameters when nargs=? or nargs=*'
            )
        kwargs.setdefault('required', required)
        super().__init__(action=action, default=default, default_cb=default_cb, **kwargs)
        self.type = normalize_input_type(type, choices)
        self.allow_leading_dash = allow_leading_dash
