"""
Custom date/time input handlers for Parameters.

.. warning::

    Uses :func:`python:locale.setlocale` if alternate locales are specified, which may cause problems on some systems.
    Using alternate locales in this manner should not be used in a multi-threaded application, as it will lead to
    unexpected output from other parts of the program.

    If you need to handle multiple locales and this is a problem for your application, then you should leave the
    ``locale`` parameters empty / ``None`` and use a proper i18n library like `babel <https://babel.pocoo.org/>`__
    for localization.

:author: Doug Skrypa
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from calendar import day_name, day_abbr
from datetime import datetime
from locale import getlocale, LC_TIME, LC_CTYPE, setlocale
from threading import Lock
from typing import TYPE_CHECKING, Union, Iterator, Optional, Tuple, List

from .base import InputType
from .exceptions import InputValidationError

if TYPE_CHECKING:
    from ..utils import Bool

__all__ = ['Day']

Locale = Union[str, Tuple[Optional[str], Optional[str]]]


class different_locale:
    """
    Context manager that allows the temporary use of an alternate locale for date/time parsing/formatting.

    Not using :class:`python:calendar.different_locale` because it results in incorrect string encoding for some
    locales (at least on Windows).
    """

    _lock = Lock()
    __slots__ = ('locale', 'original_ctype', 'original_time')

    def __init__(self, locale: Optional[Locale]):
        self.locale = locale

    def __enter__(self):
        self._lock.acquire()
        locale = self.locale
        if not locale:
            return
        self.original_ctype = getlocale(LC_CTYPE)
        self.original_time = getlocale(LC_TIME)
        setlocale(LC_TIME, locale)  # This is what calendar.different_locale used
        setlocale(LC_CTYPE, locale)  # This is required for str encoding to work as expected

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locale:
            setlocale(LC_TIME, self.original_time)
            setlocale(LC_CTYPE, self.original_ctype)
        self._lock.release()


class DateTimeInput(InputType, ABC):
    dt_type: str
    formats: List[str]
    locale: Optional[Locale]

    def __init_subclass__(cls, dt_type: str):  # noqa
        cls.dt_type = dt_type

    def __init__(self, formats: List[str], locale: Locale = None):
        self.formats = formats
        self.locale = locale

    @abstractmethod
    def choice_str(self, choice_delim: str = ',') -> str:
        raise NotImplementedError

    def format_metavar(self, choice_delim: str = ',') -> str:
        return '{' + self.choice_str(choice_delim) + '}'

    def parse_dt(self, value: str) -> datetime:
        with different_locale(self.locale):
            for fmt in self.formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    pass
        raise ValueError(f'Expected a {self.dt_type} matching the following: {self.choice_str()}')


class Day(DateTimeInput, dt_type='day of the week'):
    _str_formatters = {'%A': day_name, '%a': day_abbr}
    _num_formatters = {'%u': True, '%w': False}

    def __init__(
        self,
        *,
        full: Bool = True,
        abbreviation: Bool = True,
        numeric: Bool = False,
        iso: Bool = False,
        locale: Locale = None,
        out_format: str = '%A',
        out_numeric: Bool = False,
        out_iso: Bool = False,
        out_locale: Locale = None,
    ):
        """
        Input type representing a day of the week.

        :param full: Allow the full day name to be provided
        :param abbreviation: Allow abbreviations of day names to be provided
        :param numeric: Allow weekdays to be specified as a decimal number
        :param iso: Ignored if ``numeric`` is False.  If True, then numeric weekdays are treated as ISO 8601 weekdays,
          where 1 is Monday and 7 is Sunday.  If False, then 0 is Monday and 6 is Sunday.
        :param locale: An alternate locale to use when parsing input
        :param out_format: Weekday output format
        :param out_numeric: True to return the parsed weekday as a decimal number, False to return it as a string
        :param out_iso: Ignored if ``out_numeric`` is not True.  If True, then the ISO numeric weekday will be returned.
        :param out_locale: Alternate locale to use for output.  Defaults to the same value as ``locale``.
        """
        formats = []
        if full:
            formats.append('%A')
        if abbreviation:
            formats.append('%a')
        if numeric:
            formats.append('%u' if iso else '%w')
        if not formats:
            raise ValueError('At least one of full, abbreviation, or numeric must be True')
        super().__init__(formats, locale)
        self.full = full
        self.abbreviation = abbreviation
        self.numeric = numeric
        self.iso = iso
        self.out_format = out_format
        self.out_numeric = out_numeric
        self.out_iso = out_iso
        self.out_locale = out_locale or self.locale

    def _weekdays(self) -> Iterator[Tuple[int, str]]:
        if not self.full and not self.abbreviation:
            return
        with different_locale(self.locale):
            if self.full:
                yield from enumerate(day_name)
            if self.abbreviation:
                yield from enumerate(day_abbr)

    def choice_str(self, choice_delim: str = ',') -> str:
        choices = [dow for _, dow in self._weekdays()]
        if self.numeric:
            start, stop = (1, 8) if self.iso else (0, 7)
            choices.extend(map(str, range(start, stop)))

        return choice_delim.join(choices)

    def _parse_dow_num(self, value: str) -> int:
        start, stop = (1, 7) if self.iso else (0, 6)
        try:
            dow_num = int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid numeric weekday={value!r}') from e

        if start <= dow_num <= stop:
            return (dow_num - 1) if self.iso else dow_num

        with different_locale(self.locale):
            raise InputValidationError(
                f'Invalid weekday={dow_num} - expected a value'
                f' between {start} ({day_name[0]}) and {stop} ({day_name[6]})'
            )

    def parse_dow(self, value: str) -> int:
        """
        Parse the day of week from the given value.

        This method does not use :meth:`python:datetime.strptime` because it is not accurate for standalone numeric
        weekdays.

        :param value: The value provided as input
        :return: The numeric weekday (non-ISO)
        """
        if self.numeric:
            try:
                return self._parse_dow_num(value)
            except InputValidationError:
                raise
            except ValueError:
                pass

        choice_map = {dow.casefold(): i for i, dow in self._weekdays()}
        try:
            return choice_map[value.casefold()]
        except KeyError:
            pass

        raise InputValidationError(f'Expected a {self.dt_type} matching the following: {self.choice_str()}')

    def _format_weekday(self, day_num: int) -> str:
        try:
            weekdays = self._str_formatters[self.out_format]
        except KeyError:
            pass
        else:
            with different_locale(self.out_locale):
                return weekdays[day_num]

        raise ValueError(f'Unexpected output format={self.out_format!r} for weekday={day_num}')

    def __call__(self, value: str) -> Union[str, int]:
        day_num = self.parse_dow(value)
        if self.out_numeric:
            return (day_num + 1) if self.out_iso else day_num

        try:
            iso = self._num_formatters[self.out_format]
        except KeyError:
            pass
        else:
            return str((day_num + 1) if iso else day_num)

        return self._format_weekday(day_num)
