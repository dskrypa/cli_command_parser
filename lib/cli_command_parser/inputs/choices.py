"""
Custom input handlers for Parameters to restrict allowed values to a set of choices.

:author: Doug Skrypa
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Type, TypeVar, Collection, Iterator, Optional, Set, Mapping

from ..utils import Bool
from .base import InputType, TypeFunc
from .exceptions import InvalidChoiceError

__all__ = ['Choices', 'ChoiceMap', 'EnumChoices']

EnumT = TypeVar('EnumT', bound=Enum)


class _ChoicesBase(InputType, ABC):
    choices: Collection[Any]
    type: Optional[TypeFunc] = None
    case_sensitive: bool = True

    def __contains__(self, value: str) -> bool:
        try:
            self(value)
        except InvalidChoiceError:
            return False
        return True

    def _type_str(self) -> str:
        return f'type={self.type.__name__}, ' if self.type is not None else ''

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'<{cls_name}[{self._type_str()}case_sensitive={self.case_sensitive}, choices=({self._choices_repr()})]>'

    @abstractmethod
    def _choices_repr(self, delim: str = ',') -> str:
        raise NotImplementedError

    def _normalize(self, value: str) -> Any:
        if self.type is not None:
            try:
                return self.type(value)  # pylint: disable=E1102
            except (ValueError, TypeError) as e:
                raise InvalidChoiceError(value, self.choices) from e
        return value

    def _iter_normalized(self, value: Any, choices: Collection = None) -> Iterator[Any]:
        yield value
        if not self.case_sensitive and (choices is None or isinstance(choices, (Set, Mapping))):
            yield value.lower()
            yield value.upper()

    def _case_insensitive_map_choice(self, value: Any) -> Any:
        if not self.case_sensitive:
            norm_value = value.casefold()
            for choice, val in self.choices.items():  # noqa
                if norm_value == choice.casefold():
                    return val

        raise InvalidChoiceError(value, self.choices)

    def format_metavar(self, choice_delim: str = ',') -> str:
        return '{{{}}}'.format(choice_delim.join(map(str, self.choices)))


class Choices(_ChoicesBase):
    """
    Validates that values are members of the collection of allowed values.

    :param choices: A collection of choices allowed for a given Parameter.
    :param type: Called before evaluating whether a value matches one of the allowed choices, if provided.  Must accept
      a single string argument.
    :param case_sensitive: Whether choices should be case-sensitive.  Defaults to True.  If the choices values are not
      all strings, then this cannot be set to False.
    """

    def __init__(self, choices: Collection[Any], type: TypeFunc = None, case_sensitive: Bool = True):  # noqa
        if not case_sensitive and not all(isinstance(c, str) for c in choices):
            raise TypeError(f'Cannot combine case_sensitive=False with non-str choices={choices}')
        elif isinstance(type, EnumChoices) and not any(isinstance(c, type.enum) for c in choices):
            raise TypeError(f'Invalid choices={choices} for type={type}')

        self.choices = choices
        self.type = type
        self.case_sensitive = case_sensitive

    def _choices_repr(self, delim: str = ',') -> str:
        return delim.join(map(repr, sorted(self.choices)))

    def __call__(self, value: str) -> Any:
        choices = self.choices
        value = self._normalize(value)
        for val in self._iter_normalized(value, choices):
            if val in choices:
                return value

        if not self.case_sensitive:
            norm_value = value.casefold()
            for choice in choices:
                if norm_value == choice.casefold():
                    return choice

        raise InvalidChoiceError(value, choices)


class ChoiceMap(Choices):
    """
    Similar to :class:`Choices`, but requires a mapping for allowed values.

    :param choices: Mapping (dict) where for a given key=value pair, the key is the value that is expected to be
      provided as an argument, and the value is what should be stored in the Parameter for that argument.
    :param type: Called before evaluating whether a value matches one of the allowed choices, if provided.  Must accept
      a single string argument.
    :param case_sensitive: Whether choices should be case-sensitive.  Defaults to True.  If the choices keys are not
      all strings, then this cannot be set to False.
    """

    choices: Mapping[Any, Any]

    def __init__(self, choices: Mapping[Any, Any], *args, **kwargs):
        super().__init__(choices, *args, **kwargs)

    def __call__(self, value: str) -> Any:
        value = self._normalize(value)
        for val in self._iter_normalized(value):
            try:
                return self.choices[val]
            except KeyError:
                pass

        return self._case_insensitive_map_choice(value)


class EnumChoices(_ChoicesBase):
    """
    Similar to :class:`ChoiceMap`, but uses an Enum to validate / normalize input instead of the keys in a dict.

    :param enum: A subclass of :class:`python:enum.Enum`.
    :param case_sensitive: Whether choices should be case-sensitive.  Defaults to False.
    """

    enum: Type[EnumT]

    def __init__(self, enum: Type[EnumT], case_sensitive: Bool = False):
        self.enum = enum
        self.case_sensitive = case_sensitive
        self.choices = enum._member_map_

    def _type_str(self) -> str:
        return f'type={self.enum.__name__}, '

    def _choices_repr(self, delim: str = ',') -> str:
        return delim.join(self.enum._member_map_)

    def __call__(self, value: str) -> EnumT:
        enum = self.enum
        for val in self._iter_normalized(value):
            try:
                return enum[val]
            except KeyError:
                pass
            try:
                return enum(val)
            except ValueError:
                pass

        return self._case_insensitive_map_choice(value)
