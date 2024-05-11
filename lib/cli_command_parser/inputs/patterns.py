"""
Custom regex/glob input validation handlers for Parameters

:author: Doug Skrypa
"""

from __future__ import annotations

import os
import re
from abc import ABC
from enum import Enum
from fnmatch import translate
from typing import Collection, Dict, Match, Pattern, Sequence, Tuple, TypeVar, Union

from ..utils import MissingMixin
from .base import InputType, T
from .exceptions import InputValidationError

__all__ = ['Regex', 'RegexMode', 'Glob']

RegexResult = TypeVar('RegexResult', str, Match, Tuple[str, ...], Dict[str, str])


class PatternInput(InputType[T], ABC):
    __slots__ = ('patterns',)
    patterns: tuple[Pattern, ...]

    def _pattern_strings(self, sort: bool = False) -> Sequence[str]:
        patterns = [p.pattern for p in self.patterns]
        if sort:
            patterns.sort()
        return patterns

    def format_metavar(self, choice_delim: str = ' | ', sort_choices: bool = False) -> str:
        return choice_delim.join(self._pattern_strings(sort_choices))

    def _describe_patterns(self) -> str:
        patterns = self._pattern_strings()
        if len(patterns) == 1:
            return f'this pattern: {patterns[0]}'
        return 'any of the following patterns:\n' + '\n'.join(f'  - {p}' for p in patterns)


class RegexMode(MissingMixin, Enum):
    """The RegexMode for a given Regex input governs the type of value it returns during parsing."""

    # fmt: off
    STRING = 'string'   #: Return the full original string if it matches a given pattern
    MATCH = 'match'     #: Return a :ref:`Match <python:match-objects>` object
    GROUP = 'group'     #: Return the string from the specified capturing group
    GROUPS = 'groups'   #: Return a tuple containing all captured groups, or specific captured groups
    DICT = 'dict'       #: Return a dictionary containing all named capturing groups and their captured values
    # fmt: on

    @classmethod
    def normalize(cls, value: Union[str, RegexMode, None], group, groups) -> RegexMode:
        if value is None:
            if group is not None:
                return cls.GROUP
            elif groups:
                return cls.GROUPS
            return cls.STRING

        mode = cls(value)
        if group is not None and mode != cls.GROUP:
            raise ValueError(f'Invalid regex mode={value!r} - only GROUP is supported when a group is specified')
        elif groups and mode != cls.GROUPS:
            raise ValueError(f'Invalid regex mode={value!r} - only GROUPS is supported when groups are specified')
        return mode


class Regex(PatternInput[RegexResult]):
    """
    Validates that values match one of the provided regex patterns.  Patterns may be provided as strings, or as
    pre-compiled patterns (i.e., the result of calling :func:`python:re.compile`).  To include flags like
    :data:`python:re.IGNORECASE`, pre-compiled patterns must be used.

    Matches are checked for using :meth:`python:re.Pattern.search`, so if full matches or matches that start at the
    beginning of the string are necessary, then start (``^``) / end (``$``) anchors should be included where
    appropriate.  See :ref:`python:search-vs-match` for more related info, or
    `regular-expressions.info <https://www.regular-expressions.info/>`__ for more general info about writing regular
    expressions.

    :param patterns: One or more regex pattern strings or pre-compiled :ref:`python:re-objects` objects.
    :param group: Identifier for a capturing group.  If specified, the string captured in this group will be returned
      instead of the full / original input string.
    :param groups: Collection of identifiers for capturing groups.  If specified, a tuple containing the strings from
      the specified capturing groups will be returned instead of the full / original input string.
    :param mode: The :class:`RegexMode` (or string name of a RegexMode member) representing the type of value that
      should be returned during parsing.  When a value is provided for ``group`` or ``groups``, this does not need to
      be explicitly provided - it will automatically pick the appropriate mode.  Defaults to ``STRING``.
    """

    __slots__ = ('mode', 'group', 'groups')

    def __init__(
        self,
        *patterns: Union[str, Pattern],
        group: Union[str, int] = None,
        groups: Collection[Union[str, int]] = None,
        mode: Union[RegexMode, str] = None,
    ):
        if not patterns:
            raise TypeError('At least one regex pattern is required')
        elif group is not None and groups is not None:
            raise TypeError(f'Invalid combination of {group=} with {groups=} - only one may be provided')
        super().__init__()  # fix_default is not implemented here, so it's not necessary to expose
        self.mode = mode = RegexMode.normalize(mode, group, groups)
        self.patterns = tuple(re.compile(p) if isinstance(p, str) else p for p in patterns)
        self.group = 0 if group is None and mode == RegexMode.GROUP else group
        self.groups = groups

    def __repr__(self) -> str:
        mode, group, groups, patterns = self.mode, self.group, self.groups, self.patterns
        return f'<{self.__class__.__name__}({mode=}, {group=}, {groups=}, {patterns=})>'

    def __call__(self, value: str) -> RegexResult:
        if not (m := next((pm for p in self.patterns if (pm := p.search(value))), None)):
            raise InputValidationError(f'expected a value matching {self._describe_patterns()}')

        if (mode := self.mode) == RegexMode.STRING:
            return value
        elif mode == RegexMode.MATCH:
            return m
        elif mode == RegexMode.GROUP:
            return m.group(self.group)
        elif mode == RegexMode.GROUPS:
            if self.groups:
                return tuple(m.group(g) for g in self.groups)
            return m.groups()
        else:  # mode == RegexMode.DICT
            return m.groupdict()


class Glob(PatternInput[str]):
    """
    Validates that values match one of the provided glob / :doc:`fnmatch <python:library/fnmatch>` patterns.

    :param patterns: One or more glob pattern strings.
    :param match_case: Whether matches should be case sensitive or not (default: False).
    :param normcase: Whether :func:`python:os.path.normcase` should be called on patterns and values (default: False).
    """

    __slots__ = ('_original_patterns', 'normcase')

    def __init__(self, *patterns: str, match_case: bool = False, normcase: bool = False):
        if not patterns:
            raise TypeError('At least one glob/fnmatch pattern is required')
        super().__init__()  # fix_default is not implemented here, so it's not necessary to expose
        if normcase:
            patterns = tuple(os.path.normcase(p) for p in patterns)
        self._original_patterns = patterns
        if match_case:
            self.patterns = tuple(re.compile(translate(p)) for p in patterns)
        else:
            self.patterns = tuple(re.compile(translate(p), re.IGNORECASE) for p in patterns)
        self.normcase = normcase

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}(patterns={self.patterns})>'

    def _pattern_strings(self, sort: bool = False) -> Sequence[str]:
        return sorted(self._original_patterns) if sort else self._original_patterns

    def __call__(self, value: str) -> str:
        if self.normcase:
            value = os.path.normcase(value)
        if any(p.match(value) for p in self.patterns):
            return value
        raise InputValidationError(f'expected a value matching {self._describe_patterns()}')
