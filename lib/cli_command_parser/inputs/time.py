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
from datetime import datetime, date, time, timedelta
from enum import Enum
from locale import LC_ALL, setlocale
from threading import RLock
from typing import Union, Iterator, Collection, Sequence, Optional, TypeVar, Type, overload
from typing import Tuple, Dict

from ..typing import T, Bool, Locale, TimeBound
from ..utils import MissingMixin
from .base import InputType
from .exceptions import InputValidationError, InvalidChoiceError

__all__ = ['DTFormatMode', 'Day', 'Month', 'DateTime', 'Date', 'Time']

DT = TypeVar('DT')

DEFAULT_DATE_FMT = '%Y-%m-%d'
DEFAULT_TIME_FMT = '%H:%M:%S'
DEFAULT_DT_FMT = '%Y-%m-%d %H:%M:%S'


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
        # to remain set to `English_United States.1252` on Windows 10, which resulted in incorrectly encoded results.
        # Using f'LC_CTYPE={locale};LC_TIME={locale}' seemed cleaner than setting LC_ALL in its entirety, but it
        # resulted in `locale.Error: unsupported locale setting` on Ubuntu/WSL.
        setlocale(LC_ALL, locale)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locale:
            setlocale(LC_ALL, self.original)
        self._lock.release()


class DTInput(InputType[T], ABC):
    dt_type: str
    locale: Optional[Locale]

    def __init_subclass__(cls, dt_type: str = None):  # noqa
        cls.dt_type = dt_type

    def __init__(self, locale: Locale = None):
        self.locale = locale

    @abstractmethod
    def choice_str(self, choice_delim: str = ',') -> str:
        raise NotImplementedError

    def fix_default(self, value: Union[str, T, None]) -> Optional[T]:
        if value is None or not isinstance(value, str):
            return value
        return self(value)


# region Calendar Unit Inputs


class DTFormatMode(MissingMixin, Enum):
    FULL = 'full'                   #: The full name of a given date/time unit
    ABBREVIATION = 'abbreviation'   #: The abbreviation of a given date/time unit
    NUMERIC = 'numeric'             #: The numeric representation of a given date/time unit
    NUMERIC_ISO = 'numeric_iso'     #: The ISO numeric representation of a given date/time unit


class CalendarUnitInput(DTInput[Union[str, int]], ABC):
    _formats: Dict[DTFormatMode, Sequence[Union[str, int]]]
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
        out_format: Union[str, DTFormatMode] = DTFormatMode.FULL,
        out_locale: Locale = None,
    ):
        """
        Input type representing a date/time unit.

        :param full: Allow the full unit name to be provided
        :param abbreviation: Allow abbreviations of unit names to be provided
        :param numeric: Allow unit values to be specified as a decimal number
        :param locale: An alternate locale to use when parsing input
        :param out_format: A :class:`DTFormatMode` or str that matches a format mode.  Defaults to full weekday name.
        :param out_locale: Alternate locale to use for output.  Defaults to the same value as ``locale``.
        """
        if not (full or abbreviation or numeric):
            raise ValueError('At least one of full, abbreviation, or numeric must be True')
        super().__init__(locale=locale)
        self.full = full
        self.abbreviation = abbreviation
        self.numeric = numeric
        self.out_format = DTFormatMode(out_format)
        self.out_locale = out_locale or self.locale
        if self.out_format not in self._formats:
            raise ValueError(f'Unsupported out_format={self.out_format} for {self.__class__.__name__} inputs')

    def _values(self) -> Iterator[Tuple[int, str]]:
        if not self.full and not self.abbreviation:
            return
        min_index = self._min_index
        with different_locale(self.locale):
            if self.full:
                yield from enumerate(self._formats[DTFormatMode.FULL][min_index:], min_index)
            if self.abbreviation:
                yield from enumerate(self._formats[DTFormatMode.ABBREVIATION][min_index:], min_index)

    def choices(self) -> Sequence[str]:
        choices = [dow for _, dow in self._values()]
        if self.numeric:
            mode = DTFormatMode.NUMERIC_ISO if getattr(self, 'iso', False) else DTFormatMode.NUMERIC
            # fmt: off
            choices.extend(map(str, self._formats[mode][self._min_index:]))
            # fmt: on
        return choices

    def choice_str(self, choice_delim: str = ',') -> str:
        return choice_delim.join(self.choices())

    def format_metavar(self, choice_delim: str = ',') -> str:
        return '{' + self.choice_str(choice_delim) + '}'

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
        if out_mode in (DTFormatMode.NUMERIC, DTFormatMode.NUMERIC_ISO):
            return self._formats[out_mode][normalized]

        try:
            names_or_abbreviations = self._formats[out_mode]
        except KeyError:
            pass
        else:
            with different_locale(self.out_locale):
                return names_or_abbreviations[normalized]

        raise ValueError(f'Unexpected output format={out_mode!r} for {self.dt_type}={normalized}')


class Day(CalendarUnitInput, dt_type='day of the week'):
    _formats = {
        DTFormatMode.FULL: day_name,
        DTFormatMode.ABBREVIATION: day_abbr,
        DTFormatMode.NUMERIC: range(7),
        DTFormatMode.NUMERIC_ISO: range(1, 8),
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
        out_format: Union[str, DTFormatMode] = DTFormatMode.FULL,
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
        :param out_format: A :class:`DTFormatMode` or str that matches a format mode.  Defaults to full weekday name.
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


class Month(CalendarUnitInput, dt_type='month', min_index=1):
    _formats = {
        DTFormatMode.FULL: month_name,
        DTFormatMode.ABBREVIATION: month_abbr,
        DTFormatMode.NUMERIC: range(13),
    }

    @overload
    def __init__(
        self,
        *,
        full: Bool = True,
        abbreviation: Bool = True,
        numeric: Bool = True,
        locale: Locale = None,
        out_format: Union[str, DTFormatMode] = DTFormatMode.FULL,
        out_locale: Locale = None,
    ):
        """
        Input type representing a month.

        :param full: Allow the full month name to be provided
        :param abbreviation: Allow abbreviations of month names to be provided
        :param numeric: Allow months to be specified as a decimal number
        :param locale: An alternate locale to use when parsing input
        :param out_format: A :class:`DTFormatMode` or str that matches a format mode.  Defaults to full month name.
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


# endregion


# region Date/Time Parse Inputs


class DateTimeInput(DTInput[DT], ABC):
    formats: Collection[str]
    _type: Type[DT]
    _earliest: TimeBound = None
    _latest: TimeBound = None

    def __init_subclass__(cls, type: Type[DT]):  # noqa
        super().__init_subclass__(dt_type=type.__name__)
        cls._type = type

    def __init__(
        self, formats: Collection[str], locale: Locale = None, earliest: TimeBound = None, latest: TimeBound = None
    ):
        super().__init__(locale=locale)
        self.formats = formats
        self.earliest = earliest
        self.latest = latest

    @classmethod
    def _fix_type(cls, dt: datetime) -> DT:
        try:
            return getattr(dt, cls.dt_type)()
        except AttributeError:
            return dt

    @property
    def earliest(self) -> Optional[DT]:
        return self._fix_type(normalize_dt(self._earliest))

    @earliest.setter
    def earliest(self, value: TimeBound):
        self._validate_bound_combo(value, self._latest)
        self._earliest = value

    @property
    def latest(self) -> Optional[DT]:
        return self._fix_type(normalize_dt(self._latest))

    @latest.setter
    def latest(self, value: TimeBound):
        self._validate_bound_combo(self._earliest, value)
        self._latest = value

    @classmethod
    def _validate_bound_combo(cls, raw_earliest: TimeBound, raw_latest: TimeBound):
        earliest = cls._fix_type(normalize_dt(raw_earliest))
        latest = cls._fix_type(normalize_dt(raw_latest))
        if earliest is not None and latest is not None and earliest >= latest:
            raise ValueError(
                f'Invalid combination of earliest={raw_earliest!r} and latest={raw_latest!r} values'
                f' - {dt_repr(earliest, False)} >= {dt_repr(latest, False)}'
            )

    def parse_dt(self, value: str) -> datetime:
        with different_locale(self.locale):
            for fmt in self.formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    pass

        raise InputValidationError(
            f'Expected a {self.dt_type} matching one of the following formats: {self.choice_str()}'
        )

    def parse(self, value: str) -> DT:
        return self._fix_type(self.parse_dt(value))

    def choice_str(self, choice_delim: str = ' | ') -> str:
        return choice_delim.join(self.formats)

    def format_metavar(self, choice_delim: str = ' | ') -> str:
        choices = '{' + self.choice_str(choice_delim) + '}'
        earliest, latest = self.earliest, self.latest
        prefix = f'{dt_repr(earliest, False)} <= ' if earliest is not None else ''
        suffix = f' <= {dt_repr(latest, False)}' if latest is not None else ''
        return f'[{prefix}{choices}{suffix}]' if prefix or suffix else choices

    def _validate_bounds(self, dt: DT):
        earliest, latest = self.earliest, self.latest
        check_earliest = earliest is not None
        check_latest = latest is not None
        if not (check_earliest or check_latest):
            return
        elif (check_earliest and dt < earliest) or (check_latest and dt > latest):
            if check_earliest and check_latest:
                msg = f'between {dt_repr(earliest)} and {dt_repr(latest)} (inclusive)'
            else:
                msg = f'after {dt_repr(earliest)}' if check_earliest else f'before {dt_repr(latest)}'
            raise InputValidationError(f'Invalid {self.dt_type}={dt_repr(dt)} - a {self.dt_type} {msg} is required')

    def __call__(self, value: str) -> DT:
        parsed = self.parse(value)
        self._validate_bounds(parsed)
        return parsed


class DateTime(DateTimeInput[datetime], type=datetime):
    def __init__(self, *formats: str, locale: Locale = None, earliest: TimeBound = None, latest: TimeBound = None):
        """
        Input type that accepts any number of datetime format strings for parsing input.  Parsing results in returning
        a :class:`python:datetime.datetime` object.

        :param formats: One or more :ref:`datetime format strings <python:strftime-strptime-behavior>`.  Defaults to
          :data:`DEFAULT_DT_FMT`.
        :param locale: An alternate locale to use when parsing input
        :param earliest: If specified, the parsed value must be later than or equal to this
        :param latest: If specified, the parsed value must be earlier than or equal to this
        """
        super().__init__(formats or (DEFAULT_DT_FMT,), locale=locale, earliest=earliest, latest=latest)


class Date(DateTimeInput[date], type=date):
    def __init__(self, *formats: str, locale: Locale = None, earliest: TimeBound = None, latest: TimeBound = None):
        """
        Input type that accepts any number of datetime format strings for parsing input.  Parsing results in returning
        a :class:`python:datetime.date` object.

        :param formats: One or more :ref:`datetime format strings <python:strftime-strptime-behavior>`.  Defaults to
          :data:`DEFAULT_DT_FMT`.
        :param locale: An alternate locale to use when parsing input
        :param earliest: If specified, the parsed value must be later than or equal to this
        :param latest: If specified, the parsed value must be earlier than or equal to this
        """
        super().__init__(formats or (DEFAULT_DATE_FMT,), locale=locale, earliest=earliest, latest=latest)


class Time(DateTimeInput[time], type=time):
    def __init__(self, *formats: str, locale: Locale = None, earliest: TimeBound = None, latest: TimeBound = None):
        """
        Input type that accepts any number of datetime format strings for parsing input.  Parsing results in returning
        a :class:`python:datetime.time` object.

        :param formats: One or more :ref:`datetime format strings <python:strftime-strptime-behavior>`.  Defaults to
          :data:`DEFAULT_DT_FMT`.
        :param locale: An alternate locale to use when parsing input
        :param earliest: If specified, the parsed value must be later than or equal to this
        :param latest: If specified, the parsed value must be earlier than or equal to this
        """
        super().__init__(formats or (DEFAULT_TIME_FMT,), locale=locale, earliest=earliest, latest=latest)


# endregion


def dt_repr(dt: Union[datetime, date, time], use_repr: bool = True) -> str:
    try:
        dt_str = dt.isoformat(' ')
    except (TypeError, ValueError):  # TypeError for date objects, ValueError for time objects
        dt_str = dt.isoformat()
    return repr(dt_str) if use_repr else dt_str


def normalize_dt(value: TimeBound, now: datetime = None) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value
    elif isinstance(value, timedelta):
        if now is None:
            now = datetime.now()
        return now + value
    elif isinstance(value, date):
        return datetime.combine(value, time())
    elif isinstance(value, time):
        today = date.today() if now is None else now.date()
        return datetime.combine(today, value)
    raise TypeError(
        f'Unexpected datetime specifier type={value.__class__.__name__} for value={value!r}'
        ' (expected datetime, date, time, timedelta, or None)'
    )
