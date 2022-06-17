"""
Custom input handlers for Parameters

:author: Doug Skrypa
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

__all__ = ['InputType']

TypeFunc = Callable[[str], Any]


class InputType(ABC):
    @abstractmethod
    def __call__(self, value: str) -> Any:
        """Process the parsed argument and convert it to the desired type"""
        raise NotImplementedError

    def is_valid_type(self, value: str) -> bool:  # pylint: disable=W0613
        """
        Called during parsing when :meth:`.Parameter.would_accept` is called to determine if the value would be
        accepted later for processing / conversion via :meth:`.__call__`.  May be overridden in subclasses to
        provide actual validation, if necessary.

        Not called by :meth:`.Parameter.take_action` - value validation should happen in :meth:`.__call__`

        :param value: A parsed argument
        :return: True if this input would accept it for processing later (where it may still be rejected), False if
          it should be rejected before attempting to process / convert / store it.
        """
        return True

    def format_metavar(self, choice_delim: str = ',') -> str:
        # TODO: Optional/required arg, or handle wrapping in []/{} in formatter
        raise NotImplementedError
