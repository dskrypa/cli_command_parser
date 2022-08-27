#!/usr/bin/env python

from unittest import main, TestCase
from unittest.mock import patch

from cli_command_parser import Command, Option
from cli_command_parser.core import get_params
from cli_command_parser.exceptions import UsageError
from cli_command_parser.inputs.time import Day, different_locale
from cli_command_parser.inputs.exceptions import InvalidChoiceError, InputValidationError
from cli_command_parser.testing import ParserTest

# fmt: off
ISO_DAYS = {
    '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday', '4': 'Thursday', '5': 'Friday', '6': 'Saturday', '7': 'Sunday'
}
NON_ISO_DAYS = {
    '0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday', '4': 'Friday', '5': 'Saturday', '6': 'Sunday'
}
# fmt: on


class DayInputTest(TestCase):
    def test_setlocale_not_called_without_locale(self):
        with patch('cli_command_parser.inputs.time.setlocale') as setlocale:
            with different_locale(None):
                pass

        self.assertFalse(setlocale.called)

    # region Alternate Locale Handling

    def test_ko_in_en_out(self):
        self.assertEqual('monday', Day(locale='ko_KR', out_locale='en_US')('월요일').casefold())

    def test_en_in_fr_out(self):
        self.assertEqual('lundi', Day(locale='en_US', out_locale='fr_FR')('Monday').casefold())

    # endregion

    # region Numeric Input / Output

    def test_numeric_input_iso(self):
        day = Day(numeric=True, iso=True, out_locale='en_US')
        self.assertDictEqual(ISO_DAYS, {num: day(num) for num in ISO_DAYS})

    def test_numeric_input_non_iso(self):
        day = Day(numeric=True, out_locale='en_US')
        self.assertDictEqual(NON_ISO_DAYS, {num: day(num) for num in NON_ISO_DAYS})

    def test_invalid_numeric_input(self):
        with self.assertRaisesRegex(InputValidationError, 'Invalid weekday=9'):
            Day(numeric=True).parse_dow('9')

    def test_numeric_output_iso(self):
        day = Day(locale='en_US', out_format='numeric_iso')
        self.assertDictEqual(ISO_DAYS, {str(day(dow)): dow for dow in ISO_DAYS.values()})

    def test_numeric_output_non_iso(self):
        day = Day(locale='en_US', out_format='numeric')
        self.assertDictEqual(NON_ISO_DAYS, {str(day(dow)): dow for dow in NON_ISO_DAYS.values()})

    # endregion

    # region Input / Option Validation

    def test_format_required(self):
        with self.assertRaisesRegex(ValueError, 'At least one of .* must be True'):
            Day(full=False, abbreviation=False)

    def test_full_rejected_on_abbr_only(self):
        for kwargs in ({}, {'numeric': True}):
            with self.assertRaisesRegex(InputValidationError, 'Expected a day of the week matching the following'):
                Day(locale='en_US', full=False, **kwargs)('Monday')

    def test_bad_output_format_value(self):
        with self.assertRaisesRegex(ValueError, 'is not a valid FormatMode'):
            Day(out_format='%Y', numeric=True)('1')

    def test_bad_output_format_type(self):
        with self.assertRaisesRegex(ValueError, 'is not a valid FormatMode'):
            Day(out_format=None, numeric=True)('1')  # noqa

    def test_bad_output_format_set_late(self):
        day = Day(numeric=True)
        day.out_format = 'test'
        with self.assertRaisesRegex(ValueError, 'Unexpected output format='):
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


class ParseInputTest(ParserTest):
    pass


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
