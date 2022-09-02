"""
PassThru Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Collection, Any

from ..context import ctx
from ..exceptions import ParamUsageError, MissingArgument
from ..nargs import Nargs
from ..utils import _NotSet
from .base import Parameter, parameter_action

if TYPE_CHECKING:
    from ..typing import Bool

__all__ = ['PassThru']


class PassThru(Parameter):
    """
    Collects all remaining arguments, without processing them.  Must be preceded by ``--`` and a space.

    :param action: The action to take on individual parsed values.  Only ``store_all`` (the default) is supported
      for this parameter type.
    :param kwargs: Additional keyword arguments to pass to :class:`.Parameter`.
    """

    nargs = Nargs('*')
    missing_hint: str = "missing pass thru args separated from others with '--'"

    def __init__(self, action: str = 'store_all', default: Any = _NotSet, required: Bool = False, **kwargs):
        if not required and default is _NotSet:
            default = None
        super().__init__(action=action, required=required, default=default, **kwargs)

    @parameter_action
    def store_all(self, values: Collection[str]):
        ctx.set_parsed_value(self, values)

    def take_action(  # pylint: disable=W0237
        self, values: Collection[str], short_combo: bool = False, opt_str: str = None
    ):
        value = ctx.get_parsed_value(self)
        if value is not _NotSet:
            raise ParamUsageError(self, f'received values={values!r} but a stored value={value!r} already exists')

        ctx.record_action(self)
        normalized = list(map(self.prepare_value, values))
        action_method = getattr(self, self.action)
        return action_method(normalized)

    def result_value(self) -> Any:
        value = ctx.get_parsed_value(self)
        if value is _NotSet:
            if self.required:
                raise MissingArgument(self)
            return self.default
        return value

    result = result_value
