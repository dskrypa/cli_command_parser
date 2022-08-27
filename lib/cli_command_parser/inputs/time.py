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
from calendar import day_name, day_abbr, month_name, month_abbr
from datetime import datetime
from enum import Enum
from locale import LC_ALL, setlocale
from threading import RLock
from typing import TYPE_CHECKING, Union, Iterator, Collection, Sequence, Optional, overload, Tuple, Dict

from ..utils import MissingMixin
from .base import InputType
from .exceptions import InputValidationError, InvalidChoiceError

if TYPE_CHECKING:
    from ..utils import Bool

__all__ = ['FormatMode', 'Day', 'Month']

Locale = Union[str, Tuple[Optional[str], Optional[str]]]


class different_locale:
    """
    Context manager that allows the temporary use of an alternate locale for date/time parsing/formatting.

    Not using :class:`python:calendar.different_locale` because it results in incorrect string encoding for some
    locales (at least on Windows).
    """

    _lock = RLock()
    __slots__ = ('locale', 'original')

    def __init__(self, locale: Optional[Locale]):
        self.locale = locale

    def __enter__(self):
        self._lock.acquire()
        locale = self.locale
        if not locale:
            return
        # locale.getlocale does not support LC_ALL, but `setlocale(LC_ALL)` with no locale to set will return a str
        # containing all of the current locale settings as `key1=val1;key2=val2;...;keyN=valN`
        self.original = setlocale(LC_ALL)
        # The calendar.different_locale implementation only calls setlocale with LC_TIME, which caused LC_CTYPE
        # to remain set to `English_United States.1252` on Windows 10, which resulted in incorrectly encoded results
        setlocale(LC_ALL, f'LC_CTYPE={locale};LC_TIME={locale}')  # a subset of vars only affects the specified ones

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locale:
            setlocale(LC_ALL, self.original)
        self._lock.release()


class DateTimeInput(InputType, ABC):
    dt_type: str
    formats: Collection[str]
    locale: Optional[Locale]

    def __init_subclass__(cls, dt_type: str = None):  # noqa
        cls.dt_type = dt_type

    def __init__(self, formats: Collection[str] = (), locale: Locale = None):
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


class FormatMode(MissingMixin, Enum):
    FULL = 'full'                   #: The full name of a given date/time unit
    ABBREVIATION = 'abbreviation'   #: The abbreviation of a given date/time unit
    NUMERIC = 'numeric'             #: The numeric representation of a given date/time unit
    NUMERIC_ISO = 'numeric_iso'     #: The ISO numeric representation of a given date/time unit


class _DatetimeUnitInput(DateTimeInput, ABC):
    _formats: Dict[FormatMode, Sequence[Union[str, int]]]
    _min_index: int = 0

    def __init_subclass__(cls, min_index: int = 0, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._min_index = min_index

    def __init__(
        self,
        *,
        full: Bool = True,
        abbreviation: Bool = True,
        numeric: Bool = False,
        locale: Locale = None,
        out_format: Union[str, FormatMode] = FormatMode.FULL,
        out_locale: Locale = None,
    ):
        """
        Input type representing a date/time unit.

        :param full: Allow the full unit name to be provided
        :param abbreviation: Allow abbreviations of unit names to be provided
        :param numeric: Allow unit values to be specified as a decimal number
        :param locale: An alternate locale to use when parsing input
        :param out_format: A :class:`FormatMode` or str that matches a format mode.  Defaults to full weekday name.
        :param out_locale: Alternate locale to use for output.  Defaults to the same value as ``locale``.
        """
        if not (full or abbreviation or numeric):
            raise ValueError('At least one of full, abbreviation, or numeric must be True')
        super().__init__(locale=locale)
        self.full = full
        self.abbreviation = abbreviation
        self.numeric = numeric
        self.out_format = FormatMode(out_format)
        self.out_locale = out_locale or self.locale
        if self.out_format not in self._formats:
            raise ValueError(f'Unsupported out_format={self.out_format} for {self.__class__.__name__} inputs')

    def _values(self) -> Iterator[Tuple[int, str]]:
        if not self.full and not self.abbreviation:
            return
        min_index = self._min_index
        with different_locale(self.locale):
            if self.full:
                yield from enumerate(self._formats[FormatMode.FULL][min_index:], min_index)
            if self.abbreviation:
                yield from enumerate(self._formats[FormatMode.ABBREVIATION][min_index:], min_index)

    def choices(self) -> Sequence[str]:
        choices = [dow for _, dow in self._values()]
        if self.numeric:
            mode = FormatMode.NUMERIC_ISO if getattr(self, 'iso', False) else FormatMode.NUMERIC
            # fmt: off
            choices.extend(map(str, self._formats[mode][self._min_index:]))
            # fmt: on
        return choices

    def choice_str(self, choice_delim: str = ',') -> str:
        return choice_delim.join(self.choices())

    @abstractmethod
    def parse_numeric(self, value: str) -> int:
        raise NotImplementedError

    def parse(self, value: str) -> int:
        """
        Parse the date/time unit from the given value.

        This method does not use :meth:`python:datetime.strptime` because it is not accurate for standalone numeric
        weekdays.

        :param value: The value provided as input
        :return: The numeric unit value
        """
        if self.numeric:
            try:
                return self.parse_numeric(value)
            except InputValidationError:
                raise
            except ValueError:
                pass

        choice_map = {dow.casefold(): i for i, dow in self._values()}
        try:
            return choice_map[value.casefold()]
        except KeyError:
            pass

        raise InvalidChoiceError(value, self.choices(), self.dt_type)

    def __call__(self, value: str) -> Union[str, int]:
        normalized = self.parse(value)
        if normalized < self._min_index:
            raise InvalidChoiceError(value, self.choices(), self.dt_type)

        out_mode = self.out_format
        if out_mode in (FormatMode.NUMERIC, FormatMode.NUMERIC_ISO):
            return self._formats[out_mode][normalized]

        try:
            names_or_abbreviations = self._formats[out_mode]
        except KeyError:
            pass
        else:
            with different_locale(self.out_locale):
                return names_or_abbreviations[normalized]

        raise ValueError(f'Unexpected output format={out_mode!r} for {self.dt_type}={normalized}')


class Day(_DatetimeUnitInput, dt_type='day of the week'):
    _formats = {
        FormatMode.FULL: day_name,
        FormatMode.ABBREVIATION: day_abbr,
        FormatMode.NUMERIC: range(7),
        FormatMode.NUMERIC_ISO: range(1, 8),
    }

    @overload
    def __init__(
        self,
        *,
        full: Bool = True,
        abbreviation: Bool = True,
        numeric: Bool = False,
        iso: Bool = False,
        locale: Locale = None,
        out_format: Union[str, FormatMode] = FormatMode.FULL,
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
        :param out_format: A :class:`FormatMode` or str that matches a format mode.  Defaults to full weekday name.
        :param out_locale: Alternate locale to use for output.  Defaults to the same value as ``locale``.
        """
        ...

    def __init__(self, *, iso: Bool = False, **kwargs):
        super().__init__(**kwargs)
        self.iso = iso

    def parse_numeric(self, value: str) -> int:
        try:
            dow_num = int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid numeric weekday={value!r}') from e

        start, stop = (1, 7) if self.iso else (0, 6)
        if start <= dow_num <= stop:
            return (dow_num - 1) if self.iso else dow_num

        with different_locale(self.locale):
            raise InputValidationError(
                f'Invalid weekday={dow_num} - expected a value'
                f' between {start} ({day_name[0]}) and {stop} ({day_name[6]})'
            )


class Month(_DatetimeUnitInput, dt_type='month', min_index=1):
    _formats = {
        FormatMode.FULL: month_name,
        FormatMode.ABBREVIATION: month_abbr,
        FormatMode.NUMERIC: range(13),
    }

    @overload
    def __init__(
        self,
        *,
        full: Bool = True,
        abbreviation: Bool = True,
        numeric: Bool = True,
        locale: Locale = None,
        out_format: Union[str, FormatMode] = FormatMode.FULL,
        out_locale: Locale = None,
    ):
        """
        Input type representing a month.

        :param full: Allow the full month name to be provided
        :param abbreviation: Allow abbreviations of month names to be provided
        :param numeric: Allow months to be specified as a decimal number
        :param locale: An alternate locale to use when parsing input
        :param out_format: A :class:`FormatMode` or str that matches a format mode.  Defaults to full month name.
        :param out_locale: Alternate locale to use for output.  Defaults to the same value as ``locale``.
        """
        ...

    def __init__(self, *, numeric: Bool = True, **kwargs):
        super().__init__(numeric=numeric, **kwargs)

    def parse_numeric(self, value: str) -> int:
        try:
            month = int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid numeric weekday={value!r}') from e

        if 1 <= month <= 12:
            return month

        with different_locale(self.locale):
            raise InputValidationError(
                f'Invalid month={month} - expected a value between 1 ({month_name[1]}) and 12 ({month_name[12]})'
            )
