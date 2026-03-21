"""
PassThru Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

from typing import ClassVar, Literal

from ..nargs import Nargs
from .actions import StoreAll
from .base import Parameter

__all__ = ['PassThru']


class PassThru(Parameter, actions=(StoreAll,)):
    """
    Collects all remaining arguments, without processing them.  Must be preceded by ``--`` and a space.

    :param action: The action to take on individual parsed values.  Only ``store_all`` (the default) is supported
      for this parameter type.
    :param kwargs: Additional keyword arguments to pass to :class:`.Parameter`.
    """

    action: StoreAll
    nargs = Nargs('REMAINDER')
    # missing_hint: Hint to provide in exceptions if this param/group is missing; the leading space is intentional
    missing_hint: ClassVar[str] = " (missing pass thru args separated from others with '--')"

    def __init__(self, action: Literal['store_all'] = 'store_all', **kwargs):
        super().__init__(action=action, **kwargs)
