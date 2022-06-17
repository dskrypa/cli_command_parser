"""
PassThru Parameters

:author: Doug Skrypa
"""

from typing import Collection

from ..context import ctx
from ..exceptions import ParamUsageError
from ..nargs import Nargs
from ..utils import _NotSet
from .base import Parameter, parameter_action

__all__ = ['PassThru']


class PassThru(Parameter):
    """
    Collects all remaining arguments, without processing them.  Must be preceded by ``--`` and a space.

    :param action: The action to take on individual parsed values.  Only ``store_all`` (the default) is supported
      for this parameter type.
    :param kwargs: Additional keyword arguments to pass to :class:`Parameter`.
    """

    nargs = Nargs('*')

    def __init__(self, action: str = 'store_all', **kwargs):
        if 'choices' in kwargs:
            raise TypeError(f"{self.__class__.__name__}.__init__() got an unexpected keyword argument 'choices'")
        super().__init__(action=action, **kwargs)

    def take_action(self, values: Collection[str], short_combo: bool = False):  # pylint: disable=W0237
        value = ctx.get_parsing_value(self)
        if value is not _NotSet:
            raise ParamUsageError(self, f'received values={values!r} but a stored value={value!r} already exists')

        ctx.record_action(self)
        normalized = list(map(self.prepare_value, values))
        action_method = getattr(self, self.action)
        return action_method(normalized)

    @parameter_action
    def store_all(self, values: Collection[str]):
        ctx.set_parsing_value(self, values)
