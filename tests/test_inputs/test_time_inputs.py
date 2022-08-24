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

    def test_format_required(self):
        with self.assertRaisesRegex(ValueError, 'At least one of .* must be True'):
            Day(full=False, abbreviation=False)

    def test_ko_in_en_out(self):
        self.assertEqual('monday', Day(locale='ko_KR', out_locale='en_US')('월요일').casefold())

    def test_en_in_fr_out(self):
        self.assertEqual('lundi', Day(locale='en_US', out_locale='fr_FR')('Monday').casefold())

    def test_numeric_input_iso(self):
        day = Day(numeric=True, iso=True, out_locale='en_US')
        self.assertDictEqual(ISO_DAYS, {num: day(num) for num in ISO_DAYS})

    def test_numeric_input_non_iso(self):
        day = Day(numeric=True, out_locale='en_US')
        self.assertDictEqual(NON_ISO_DAYS, {num: day(num) for num in NON_ISO_DAYS})

    def test_invalid_numeric(self):
        with self.assertRaisesRegex(InputValidationError, 'Invalid weekday=9'):
            Day(numeric=True).parse_dow('9')

    def test_full_rejected_on_abbr_only(self):
        with self.assertRaisesRegex(InputValidationError, 'Expected a day of the week matching the following'):
            Day(locale='en_US', full=False)('Monday')

    def test_bad_output_format(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected output format='):
            Day(out_format='%Y', numeric=True)('1')


class ParseInputTest(ParserTest):
    pass


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    try:
        main(verbosity=2, exit=False)
    except KeyboardInterrupt:
        print()
