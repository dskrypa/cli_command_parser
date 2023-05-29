#!/usr/bin/env python

from datetime import datetime, date, timedelta, time
from unittest import main
from unittest.mock import patch

from cli_command_parser import Command, Option, BadArgument
from cli_command_parser.inputs.time import Day, Month, DateTime, Date, Time, different_locale, normalize_dt, dt_repr
from cli_command_parser.inputs import TimeDelta, InvalidChoiceError, InputValidationError
from cli_command_parser.testing import ParserTest, get_help_text

# fmt: off
ISO_DAYS = {
    '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday', '4': 'Thursday', '5': 'Friday', '6': 'Saturday', '7': 'Sunday'
}
NON_ISO_DAYS = {
    '0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday', '4': 'Friday', '5': 'Saturday', '6': 'Sunday'
}
MONTHS = {
    '1': 'January', '2': 'February', '3': 'March', '4': 'April', '5': 'May', '6': 'June',
    '7': 'July', '8': 'August', '9': 'September', '10': 'October', '11': 'November', '12': 'December',
}
EN_US = 'en_US.utf-8'
KO_KR = 'ko_KR.utf-8'
FR_FR = 'fr_FR.utf-8'
# fmt: on

JAN_1_2022 = date(2022, 1, 1)
FEB_2_2022 = date(2022, 2, 2)
MAR_3_2022 = date(2022, 3, 3)


class MiscDTInputTest(ParserTest):
    def test_setlocale_not_called_without_locale(self):
        with patch('cli_command_parser.inputs.time.setlocale') as setlocale:
            with different_locale(None):
                pass

        self.assertFalse(setlocale.called)

    # region normalize_dt

    def test_normalize_dt_bad_type(self):
        with self.assert_raises_contains_str(TypeError, 'Unexpected datetime specifier type=int'):
            normalize_dt(15)  # noqa

    def test_normalize_dt_timedelta(self):
        now = datetime(2000, 1, 15)
        self.assertEqual(datetime(2000, 1, 10), normalize_dt(timedelta(days=-5), now))
        self.assertEqual(datetime(2000, 1, 20), normalize_dt(timedelta(days=5), now))

    def test_normalize_dt_time(self):
        now = datetime(2000, 1, 15, 15, 30, 45)
        self.assertEqual(datetime(2000, 1, 15, 3, 40, 10), normalize_dt(time(3, 40, 10), now))

    def test_normalize_dt_date(self):
        self.assertEqual(datetime(2000, 1, 10), normalize_dt(date(2000, 1, 10)))

    def test_normalize_dt_dt(self):
        dt = datetime(2000, 1, 15, 15, 30, 45)
        self.assertIs(dt, normalize_dt(dt))

    def test_normalize_dt_none(self):
        self.assertIs(None, normalize_dt(None))

    # endregion

    # region dt_repr

    def test_dt_repr_dt(self):
        dt = datetime(2000, 1, 15, 15, 30, 45)
        self.assertEqual("'2000-01-15 15:30:45'", dt_repr(dt))
        self.assertEqual('2000-01-15 15:30:45', dt_repr(dt, False))

    def test_dt_repr_date(self):
        dt = date(2000, 1, 15)
        self.assertEqual("'2000-01-15'", dt_repr(dt))
        self.assertEqual('2000-01-15', dt_repr(dt, False))

    def test_dt_repr_time(self):
        dt = time(15, 30, 45)
        self.assertEqual("'15:30:45'", dt_repr(dt))
        self.assertEqual('15:30:45', dt_repr(dt, False))

    # endregion


class DayInputTest(ParserTest):
    # region Alternate Locale Handling

    def test_ko_in_en_out(self):
        self.assertEqual('monday', Day(locale=KO_KR, out_locale=EN_US)('월요일').casefold())

    def test_en_in_fr_out(self):
        self.assertEqual('lundi', Day(locale=EN_US, out_locale=FR_FR)('Monday').casefold())

    # endregion

    # region Numeric Input / Output

    def test_numeric_input_iso(self):
        day = Day(numeric=True, iso=True, out_locale=EN_US)
        self.assertDictEqual(ISO_DAYS, {num: day(num) for num in ISO_DAYS})

    def test_numeric_input_non_iso(self):
        day = Day(numeric=True, out_locale=EN_US)
        self.assertDictEqual(NON_ISO_DAYS, {num: day(num) for num in NON_ISO_DAYS})

    def test_invalid_numeric_input(self):
        with self.assert_raises_contains_str(InputValidationError, 'Invalid weekday=9'):
            Day(numeric=True).parse_numeric('9')

    def test_numeric_output_iso(self):
        day = Day(locale=EN_US, out_format='numeric_iso')
        self.assertDictEqual(ISO_DAYS, {str(day(dow)): dow for dow in ISO_DAYS.values()})

    def test_numeric_output_non_iso(self):
        day = Day(locale=EN_US, out_format='numeric')
        self.assertDictEqual(NON_ISO_DAYS, {str(day(dow)): dow for dow in NON_ISO_DAYS.values()})

    # endregion

    # region Input / Option Validation

    def test_format_required(self):
        with self.assertRaisesRegex(ValueError, 'At least one of .* must be True'):
            Day(full=False, abbreviation=False)

    def test_full_rejected_on_abbr_only(self):
        for kwargs in ({}, {'numeric': True}):
            with self.assertRaises(InvalidChoiceError):
                Day(locale=EN_US, full=False, **kwargs)('Monday')

    def test_bad_output_format_value(self):
        with self.assert_raises_contains_str(ValueError, 'is not a valid DTFormatMode'):
            Day(out_format='%Y', numeric=True)('1')

    def test_bad_output_format_type(self):
        with self.assert_raises_contains_str(ValueError, 'is not a valid DTFormatMode'):
            Day(out_format=None, numeric=True)('1')  # noqa

    def test_bad_output_format_set_late(self):
        day = Day(numeric=True)
        day.out_format = 'test'
        with self.assert_raises_contains_str(ValueError, 'Unexpected output format='):
            day('1')

    # endregion

    # region Help Formatting

    def test_all_choices(self):
        exp = '{Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday,Mon,Tue,Wed,Thu,Fri,Sat,Sun,0,1,2,3,4,5,6}'
        self.assertEqual(exp, Day(numeric=True).format_metavar())

    def test_full_choices(self):
        exp = '{Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday}'
        self.assertEqual(exp, Day(abbreviation=False).format_metavar())

    def test_abbr_choices(self):
        self.assertEqual('{Mon,Tue,Wed,Thu,Fri,Sat,Sun}', Day(full=False).format_metavar())

    def test_num_iso_choices(self):
        expected = '{1,2,3,4,5,6,7}'
        self.assertEqual(expected, Day(numeric=True, full=False, abbreviation=False, iso=True).format_metavar())

    # endregion


class MonthInputTest(ParserTest):
    def test_invalid_output_format(self):
        with self.assert_raises_contains_str(ValueError, 'Unsupported out_format='):
            Month(out_format='numeric_iso')

    def test_invalid_parsed_number(self):
        with patch.object(Month, 'parse', return_value=0):
            with self.assert_raises_contains_str(InvalidChoiceError, 'invalid month:'):
                Month(numeric=True)('0')

    def test_invalid_number(self):
        for case in ('0', '13', '-1'):
            with self.subTest(case=case):
                with self.assert_raises_contains_str(InputValidationError, 'expected a value between'):
                    Month(numeric=True).parse(case)

    def test_numeric_output(self):
        month = Month(out_format='numeric', locale=EN_US)
        self.assertDictEqual(MONTHS, {str(month(m)): m for m in MONTHS.values()})

    def test_numeric_input(self):
        month = Month(out_locale=EN_US)
        self.assertDictEqual(MONTHS, {n: month(n) for n in MONTHS})

    # region Help Formatting

    def test_all_choices(self):
        expected = (
            '{January,February,March,April,May,June,July,August,September,October,November,December'
            ',Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'
            ',1,2,3,4,5,6,7,8,9,10,11,12}'
        )
        self.assertEqual(expected, Month().format_metavar())

    def test_full_choices(self):
        expected = '{January,February,March,April,May,June,July,August,September,October,November,December}'
        self.assertEqual(expected, Month(abbreviation=False, numeric=False).format_metavar())

    def test_abbr_choices(self):
        expected = '{Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec}'
        self.assertEqual(expected, Month(full=False, numeric=False).format_metavar())

    def test_num_choices(self):
        expected = '{1,2,3,4,5,6,7,8,9,10,11,12}'
        self.assertEqual(expected, Month(full=False, abbreviation=False).format_metavar())

    # endregion


class TimeDeltaInputTest(ParserTest):
    def test_invalid_unit(self):
        with self.assert_raises_contains_str(TypeError, 'Invalid unit='):
            TimeDelta('foo')  # noqa

    def test_default_handling(self):
        class Foo(Command):
            foo = Option(type=TimeDelta('days'))
            bar = Option(type=TimeDelta('days'), default=2)
            baz = Option(type=TimeDelta('days'), default=timedelta(days=3))

        foo = Foo()
        self.assertIsNone(foo.foo)
        self.assertEqual(timedelta(days=2), foo.bar)
        self.assertEqual(timedelta(days=3), foo.baz)

    def test_help_text(self):
        class Foo(Command):
            bar = Option(type=TimeDelta('weeks'))

        self.assertIn('\n  --bar {weeks}\n', get_help_text(Foo))

    def test_parsing(self):
        class Foo(Command):
            bar = Option('-b', type=TimeDelta('hours'), default=2)

        cases = [
            ([], timedelta(hours=2)),
            (['-b', '123'], timedelta(hours=123)),
            (['-b', '-5'], timedelta(hours=-5)),
            (['-b', '-5.5'], timedelta(hours=-5, minutes=-30)),
            (['-b', '4.5'], timedelta(hours=4, minutes=30)),
        ]
        for args, expected in cases:
            with self.subTest(args=args, expected=expected):
                self.assertEqual(expected, Foo.parse(args).bar)

        self.assert_parse_fails(
            Foo, ['-b', 'potato'], BadArgument, "Invalid numeric hours='potato' - expected an integer or float"
        )


class DateTimeInputTest(ParserTest):
    _CASES = {
        DateTime: (datetime(2000, 1, 1, 2, 30, 45), '2000-01-01 2:30:45'),
        Date: (date(2000, 1, 1), '2000-01-01'),
        Time: (time(2, 30, 45), '2:30:45'),
    }

    def test_no_bounds(self):
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                parsed = input_cls()(dt_str)
                self.assertEqual(expected, parsed)
                self.assertIs(parsed.__class__, expected.__class__)

    def test_no_format_match(self):
        with self.assert_raises_contains_str(InputValidationError, 'matching one of the following formats'):
            Date()('2000')

    def test_bad_dt_bounds(self):
        with self.assert_raises_contains_str(ValueError, 'Invalid combination of earliest='):
            Date(earliest=date(2005, 1, 1), latest=date(2000, 1, 1))

    def test_dt_too_early(self):
        earliest_vals = (datetime(2010, 1, 1, 3), timedelta(days=-10))
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                for earliest in earliest_vals:
                    with self.assertRaisesRegex(InputValidationError, 'after .* is required'):
                        input_cls(earliest=earliest)(dt_str)

    def test_dt_too_late(self):
        dt = datetime(1999, 1, 1, 1)
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                with self.assertRaisesRegex(InputValidationError, 'before .* is required'):
                    input_cls(latest=dt)(dt_str)

    def test_dt_not_between(self):
        earliest, latest = datetime(2002, 1, 1, 0), datetime(2010, 1, 1, 1)
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                with self.assertRaisesRegex(InputValidationError, r'between .* \(inclusive\) is required'):
                    input_cls(earliest=earliest, latest=latest)(dt_str)

    def test_dt_is_after(self):
        earliest_vals = (datetime(1999, 1, 1, 1), datetime(2000, 1, 1, 2, 30, 45))
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                for earliest in earliest_vals:
                    self.assertEqual(expected, input_cls(earliest=earliest)(dt_str))

    def test_dt_is_before(self):
        latest_vals = (datetime(2005, 1, 1, 3), datetime(2000, 1, 1, 2, 30, 45))
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                for latest in latest_vals:
                    self.assertEqual(expected, input_cls(latest=latest)(dt_str))

    def test_dt_is_between(self):
        earliest, latest = datetime(1999, 1, 1, 1), datetime(2005, 1, 1, 3)
        for input_cls, (expected, dt_str) in self._CASES.items():
            with self.subTest(input_cls=input_cls, dt_str=dt_str):
                input_obj = input_cls(earliest=earliest, latest=latest)
                self.assertEqual(expected, input_obj(dt_str))

    def test_metavar_no_bounds(self):
        cases = {
            DateTime: {(): '{%Y-%m-%d %H:%M:%S}', ('%Y',): '{%Y}', ('%Y', '%Y-%m'): '{%Y | %Y-%m}'},
            Date: {(): '{%Y-%m-%d}', ('%Y',): '{%Y}', ('%Y', '%Y-%m'): '{%Y | %Y-%m}'},
            Time: {(): '{%H:%M:%S}', ('%H',): '{%H}', ('%H', '%H:%M'): '{%H | %H:%M}'},
        }
        for input_cls, cls_cases in cases.items():
            for args, expected in cls_cases.items():
                with self.subTest(input_cls=input_cls, args=args, expected=expected):
                    self.assertEqual(expected, input_cls(*args).format_metavar())

    def test_metavar_bounded(self):
        earliest, latest = datetime(2000, 1, 1), datetime(2005, 12, 31)
        self.assertEqual('[2000-01-01 <= {%Y-%m-%d}]', Date(earliest=earliest).format_metavar())
        self.assertEqual('[{%Y-%m-%d} <= 2005-12-31]', Date(latest=latest).format_metavar())
        expected = '[2000-01-01 <= {%Y-%m-%d} <= 2005-12-31]'
        self.assertEqual(expected, Date(earliest=earliest, latest=latest).format_metavar())


class ParseInputTest(ParserTest):
    def test_date_default_type_fix(self):
        class Foo(Command):
            start = Option('-s', type=Date(), default='2022-01-01')
            end = Option('-e', type=Date(), default=JAN_1_2022)

        cases = {JAN_1_2022: [], FEB_2_2022: ['-s', '2022-02-02', '-e', '2022-02-02']}
        for expected, argv in cases.items():
            with self.subTest(expected=expected, argv=argv):
                foo = Foo.parse(argv)
                self.assertEqual(expected, foo.start)
                self.assertEqual(expected, foo.end)

    def test_date_default_collection_type_fix_tuple(self):
        class Foo(Command):
            bar = Option('-b', type=Date(), nargs='+', default=('2022-01-01', JAN_1_2022))

        cases = [
            ([], [JAN_1_2022, JAN_1_2022]),
            (['-b', '2022-02-02', '2022-03-03'], [JAN_1_2022, JAN_1_2022, FEB_2_2022, MAR_3_2022]),
        ]
        for argv, expected in cases:
            with self.subTest(expected=expected, argv=argv):
                foo = Foo.parse(argv)
                self.assertEqual(expected, foo.bar)

    def test_date_default_collection_type_fix_single(self):
        class Foo(Command):
            bar = Option('-b', type=Date(), nargs='+', default=JAN_1_2022)

        cases = [
            ([], [JAN_1_2022]),
            (['-b', '2022-02-02', '2022-03-03'], [JAN_1_2022, FEB_2_2022, MAR_3_2022]),
        ]
        for argv, expected in cases:
            with self.subTest(expected=expected, argv=argv):
                foo = Foo.parse(argv)
                self.assertEqual(expected, foo.bar)

    def test_date_default_collection_type_fix_custom(self):
        class Custom:
            __slots__ = ('data',)

            def __init__(self, data):
                self.data = data

            def __iter__(self):
                yield from self.data

            def __getitem__(self, item):
                return self.data[item]

            def __len__(self):
                return len(self.data)

            def __contains__(self, item):
                return item in self.data

        default = Custom((JAN_1_2022,))

        class Foo(Command):
            bar = Option('-b', type=Date(), nargs='+', default=default)

        cases = [
            ([], [JAN_1_2022]),
            (['-b', '2022-02-02', '2022-03-03'], [JAN_1_2022, FEB_2_2022, MAR_3_2022]),
        ]
        for argv, expected in cases:
            with self.subTest(expected=expected, argv=argv):
                foo = Foo.parse(argv)
                self.assertEqual(expected, foo.bar)


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
